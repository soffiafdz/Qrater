"""
Qrater: Routes.

Module with different HTML routes for the webapp.
"""

import os
import re
import csv
import json
from shutil import rmtree
from collections import defaultdict
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import (render_template, flash, abort, redirect, url_for, request,
                   current_app, send_file)
from flask_login import current_user, login_required
from app import db
from app.upload import allowed_file
from app.main.forms import (LoadDatasetForm, UploadDatasetForm,
                            EditDatasetForm, RatingForm, ExportRatingsForm)
from app.models import Dataset, Image, Ratings, Rater
from app.main import bp


@bp.before_app_request
def before_request():
    """Record time of rater's last activity."""
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@bp.route("/", methods=['GET', 'POST'])
@bp.route("/dashboard", methods=['GET', 'POST'])
@bp.route("/<all_raters_string>", methods=['GET', 'POST'])
def dashboard(all_raters_string=None):
    """Construct the landing page."""
    # Why did I do this instead of request.args.get?
    # Gibberish URL: ABORT
    if all_raters_string is not None and all_raters_string != "all_raters":
        abort(404)
    # Convert URL to all_raters Boolean
    all_raters = 1 if all_raters_string else 0

    # Reroute to 'Welcome' landing page if there are no Datasets
    if Dataset.query.first() is None:
        return render_template('no_datasets.html', title='Dashboard',
                               rater=current_user)

    n_imgs = defaultdict(list)
    for dataset in Dataset.query.all():
        imgs = dataset.images
        ntot = imgs.count()
        if all_raters or current_user.is_anonymous:
            n_0 = imgs.join(Ratings).filter_by(rating=0).\
                union(imgs.filter_by(ratings=None)).distinct().count()
            n_1 = imgs.join(Ratings).filter_by(rating=1).distinct().count()
            n_2 = imgs.join(Ratings).filter_by(rating=2).distinct().count()
            n_3 = imgs.join(Ratings).filter_by(rating=3).distinct().count()
            n_r = sum((n_1, n_2, n_3))
        else:
            n_1 = imgs.join(Ratings).filter_by(rating=1, rater=current_user)\
                .count()
            n_2 = imgs.join(Ratings).filter_by(rating=2, rater=current_user)\
                .count()
            n_3 = imgs.join(Ratings).filter_by(rating=3, rater=current_user)\
                .count()
            n_r = sum((n_1, n_2, n_3))
            n_0 = ntot - n_r
        n1_100 = (n_1 / ntot * 100) if ntot > 0 else 0
        n2_100 = (n_2 / ntot * 100) if ntot > 0 else 0
        n3_100 = (n_3 / ntot * 100) if ntot > 0 else 0
        n_imgs['total'].append(ntot)
        n_imgs['ratings'].append(n_r)
        n_imgs['pending'].append(n_0)
        n_imgs['pass'].append(n_1)
        n_imgs['warning'].append(n_2)
        n_imgs['fail'].append(n_3)
        n_imgs['pass100'].append(round(n1_100))
        n_imgs['warning100'].append(round(n2_100))
        n_imgs['fail100'].append(round(n3_100))
    return render_template('dashboard.html', title='Dashboard',
                           Image=Image, Ratings=Ratings,
                           datasets=Dataset.query.all(),
                           all_raters=all_raters, n_imgs=n_imgs)


@bp.route('/rate/<name_dataset>', methods=['GET', 'POST'])
@login_required
def rate(name_dataset):
    """Page to view images and rate them."""
    # If dataset doesn't exist abort with 404
    dataset = Dataset.query.filter_by(name=name_dataset).first_or_404()

    # Static directory
    statics_dir = os.path.join(current_app.config['ABS_PATH'], 'static')

    # All raters
    all_raters = request.args.get('all_raters', 0, type=int)

    # Dictionary with all possible filters
    filters = {
        "image": request.args.get('image', None, type=str),
        "rating": request.args.get('rating_filter', None, type=int),
        "type": request.args.get('type_filter', None, type=str),
        "subject": request.args.get('sub_filter', None, type=str),
        "session": request.args.get('sess_filter', None, type=str)
    }

    # INIT with all dataset's images
    imgs = dataset.images

    # Paging
    pagination, page = True, request.args.get('page', 1, type=int)

    if filters["image"]:
        # If there is an image filtering, just show the image
        # There is nothing else to do (filter, query, etc...)
        img = dataset.images.filter_by(name=filters["image"]).first_or_404()

        # Rewrite imgs ## IS THIS NECESSARY??
        imgs = None

        # No need of pagination (Only 1 image); REWRITE VAR
        pagination, page = False, None

    imgs = imgs.filter_by(imgtype=filters["type"]) \
        if filters["type"] else imgs

    imgs = imgs.filter_by(subject=filters["subject"]) \
        if filters["subject"] else imgs

    imgs = imgs.filter_by(session=filters["session"]) \
        if filters["session"] else imgs

    if filters["rating"] is None:
        # If no rating_filter, no need to do anything else
        pass
    elif all_raters:
        if filters["rating"] == 0:  # PENDING
            # Images without any rating saved
            unrated = imgs.filter_by(ratings=None)

            # Images marked 'PENDING' by any rater
            pending = imgs.join(Ratings).filter_by(rating=filters["rating"])

            # QUERY: UNRATED + PENDING
            # Unless they have another rating
            imgs = pending.union(unrated).distinct()

        # For ANY other rating; just filter by rating...
        # TODO: BUG more pages than images
        elif filters["rating"] < 4:
            imgs = imgs.join(Ratings).\
                filter_by(rating=filters["rating"]).\
                distinct()

        else:   # If 'rating' is >=4, there's an ERROR, so abort w/404
            flash('Invalid filtering; Showing all images...',
                  'danger')
            return redirect(url_for('main.rate', all_raters=all_raters,
                                    name_dataset=name_dataset))
    else:
        # For single rater (current); filtering is more specific
        if filters["rating"] == 0:
            # Images with ratings from CURRENT_RATER (except pending)
            rated = imgs.join(Ratings).filter(Ratings.rater == current_user,
                                              Ratings.rating > 0)

            # All images, except Rated
            imgs = imgs.except_(rated)

        elif filters["rating"] < 4:
            # Images where rating BY CURR_RATER matches rating filter
            imgs = imgs.join(Ratings).filter_by(rating=filters["rating"],
                                                rater=current_user)
        else:  # If 'rating' is >=4, there's an ERROR, so abort w/404
            flash('Invalid filtering; Showing all images...',
                  'danger')
            return redirect(url_for('main.rate', all_raters=all_raters,
                                    name_dataset=name_dataset))

    imgs = imgs.order_by(Image.id.asc()).paginate(page, 1, False) \
        if pagination else None

    # If after filtering the query ends empty, return all of them (fuck it...)
    if pagination and not imgs.items:
        flash('Filter ran out of images in filter; Showing all images...',
              'info')
        return redirect(url_for('main.rate', all_raters=all_raters,
                                name_dataset=name_dataset))

    # Image will be first image of list; Paginate takes care of everything
    # If there's no pagination, then an image was filtered, so img is declared
    img = imgs.items[0] if pagination else img

    # Ratings from the resulting query after filtering
    all_ratings = img.ratings.all()

    # Fix PATH from database for showing the images in browser
    path = img.path.replace(f'{statics_dir}/', "")

    # Filtering boolean for HTML purposes
    filtering = bool(filters["image"] or filters["rating"] or filters["type"]
                     or filters["subject"] or filters["session"])

    # Rating form
    form = RatingForm()
    if form.validate_on_submit():
        img.set_rating(user=current_user, rating=form.rating.data)
        img.set_comment(user=current_user, comment=form.comment.data)
        return redirect(request.url)

    return render_template('rate.html', DS=dataset, form=form, imgs=imgs,
                           pagination=pagination, all_ratings=all_ratings,
                           img_name=img.name, img_path=path, title=img.name,
                           filters=filters, filtering=filtering,
                           all_raters=all_raters,
                           comment=img.comment_by_user(current_user),
                           rating=img.rating_by_user(current_user))


@bp.route('/upload-dataset', methods=['GET', 'POST'])
@login_required
def upload_dataset():
    """Page to upload new dataset of MRI."""
    data_dir = os.path.join(current_app.config['ABS_PATH'], 'static/datasets')

    form = UploadDatasetForm()
    if form.validate_on_submit():
        files = request.files.getlist(form.dataset.name)
        savedir = os.path.join(data_dir, form.dataset_name.data)

        if not os.path.isdir(savedir):
            os.makedirs(savedir)

        dataset = Dataset(name=form.dataset_name.data)
        db.session.add(dataset)
        db.session.commit()
        imgs = []
        for file in files:
            ext = file.filename.rsplit('.', 1)[1]
            if file and allowed_file(file.filename,
                                     current_app.config['DSET_ALLOWED_EXTS']):
                filename = secure_filename(file.filename)
                bname = filename.rsplit('.', 1)[0]
                fpath = os.path.join(savedir, filename)
                file.save(fpath)
                # Maybe don't save and just use "fpath" to load the image??
                img = Image(name=bname, path=fpath, extension=ext,
                            dataset=dataset)
                imgs.append(img)
            else:
                for img in imgs:
                    os.remove(img.path)
                db.session.delete(dataset)
                db.session.commit()
                flash(f'.{ext} is not a supported filetype', 'danger')
                return redirect(request.url)
        for img in imgs:
            db.session.add(img)
            db.session.commit()
        flash('File(s) successfully uploaded!', category='success')
        return redirect(url_for('main.dashboard'))
    for _, error in form.errors.items():
        flash(error[0], 'danger')
    return render_template('upload_dataset.html', form=form,
                           title='Upload Dataset')


@bp.route('/load-dataset', methods=['GET', 'POST'])
@bp.route('/load-dataset/<directory>', methods=['GET', 'POST'])
@login_required
def load_dataset(directory=None):
    """Page to load new datasets from within HOST."""
    data_dir = os.path.join(current_app.config['ABS_PATH'], 'static/datasets')

    info = {'directory': directory, 'new_imgs': 0}
    if directory is not None:
        # Count the files in the directory
        n_files = 0
        for _, _, files in os.walk(os.path.join(data_dir, directory)):
            for file in files:
                n_files += 1
        # Save useful info for template
        info['model'] = Dataset.query.filter_by(name=directory).first()
        info['saved_imgs'] = info['model'].images.count() \
            if info['model'] else 0
        info['new_imgs'] = n_files - info['saved_imgs']

    form = LoadDatasetForm()
    form.dir_name.choices = os.listdir(data_dir)
    if form.validate_on_submit():
        # If dataset is not a Dataset Model, create it.
        if not info['model']:
            info['model'] = Dataset(name=form.dir_name.data)
            db.session.add(info['model'])
            db.session.commit()

        # Loop through files
        # os.walk(path, followlinks=True) :: This would follow symlink location
        # TODO Test walk with links on BIC
        loaded_images = 0
        for root, _, files in os.walk(os.path.join(data_dir,
                                                   form.dir_name.data)):
            for file in files:
                # Check which images are already loaded
                basename = file.rsplit('.', 1)[0]
                if not Image.query.filter(Image.name == basename,
                                          Image.dataset == info['model']).\
                        first():
                    fpath = os.path.join(root, file)
                    ext = file.rsplit('.', 1)[1]
                    if allowed_file(file,
                                    current_app.config['DSET_ALLOWED_EXTS']):
                        img = Image(name=basename, path=fpath, extension=ext,
                                    dataset=info['model'])
                        db.session.add(img)
                        db.session.commit()
                        loaded_images += 1
                    else:
                        flash((f'.{ext} from {file}'
                               ' is not a supported filetype'), 'danger')
                        return redirect(url_for('main.dashboard'))
        if loaded_images > 0:
            flash((f"{loaded_images} file(s)"
                   f" were successfully loaded for {directory}"), 'success')
        return redirect(url_for('main.dashboard'))
    for _, error in form.errors.items():
        flash(error[0], 'danger')
    return render_template('load_dataset.html', form=form, title="Load",
                           dict=info)


@bp.route('/edit-dataset', methods=['GET', 'POST'])
@bp.route('/edit-dataset/<dataset>', methods=['GET', 'POST'])
@login_required
def edit_dataset(dataset=None):
    """Page to edit an existing dataset of MRI."""
    if dataset is not None:
        ds_model = Dataset.query.filter_by(name=dataset).first_or_404()

    data_dir = os.path.join(current_app.config['ABS_PATH'], 'static/datasets')

    form = EditDatasetForm()
    form.dataset.choices = [ds.name for ds in Dataset.query.order_by('name')]

    test_names = {}
    for set in Dataset.query.all():
        test_names[set.name] = [img.name for img in set.images.limit(5).all()]

    changes = False
    if form.validate_on_submit():
        if form.new_name.data and form.new_name.data != ds_model.name:
            if Dataset.query.filter_by(name=form.new_name.data).first():
                flash((f'A Dataset named "{form.new_name.data}" '
                      'already exists. Please choose another name'),
                      'danger')
                return redirect(request.url)
            os.rename(os.path.join(data_dir, ds_model.name),
                      os.path.join(data_dir, form.new_name.data))
            for img in ds_model.images.all():
                img.path = img.path.replace(ds_model.name, form.new_name.data)
                db.session.add(img)
            ds_model.name = form.new_name.data
            db.session.add(ds_model)
            db.session.commit()
            changes = True

        files = request.files.getlist(form.imgs_to_upload.name)
        if files[0].filename != "":
            savedir = os.path.join(data_dir, ds_model.name)
            new_imgs = []
            for file in files:
                ext = file.filename.rsplit('.', 1)[1]
                if file and \
                        allowed_file(file.filename,
                                     current_app.config['DSET_ALLOWED_EXTS']):
                    filename = secure_filename(file.filename)
                    bname = filename.rsplit('.', 1)[0]
                    fpath = os.path.join(savedir, filename)
                    file.save(fpath)
                    img = Image(name=bname, path=fpath, extension=ext,
                                dataset=ds_model)
                    new_imgs.append(img)
                else:
                    # First delete all uploaded new images then exit w/error
                    for img in new_imgs:
                        os.remove(img.path)
                    flash(f'.{ext} is not a supported filetype', 'danger')
                    return redirect(request.url)
            for img in new_imgs:
                db.session.add(img)
                db.session.commit()
            changes = True

        if form.sub_regex.data \
                or form.sess_regex.data \
                or form.type_regex.data:
            for img in ds_model.images.all():
                img_change = False
                if form.sub_regex.data:
                    pattern = form.sub_regex.data
                    result = re.search(pattern, img.name)
                    if result:
                        img.subject = result.group()
                        img_change = True
                if form.sess_regex.data:
                    pattern = form.sess_regex.data
                    result = re.search(pattern, img.name)
                    if result:
                        img.session = result.group()
                        img_change = True
                if form.type_regex.data:
                    pattern = form.type_regex.data
                    result = re.search(pattern, img.name)
                    if result:
                        img.imgtype = result.group()
                        img_change = True
                if img_change:
                    db.session.add(img)
                    db.session.commit()
            changes = True

        if changes:
            flash(f'{ds_model.name} successfully edited!', 'success')
            return redirect(url_for('main.dashboard'))
    return render_template('edit_dataset.html', form=form, dataset=dataset,
                           names=test_names, title='Edit Dataset')


@bp.route('/delete-dataset/<dataset>')
@login_required
def delete_dataset(dataset):
    """Page to delete a dataset of MRI, including images and ratings."""
    ds_model = Dataset.query.filter_by(name=dataset).first_or_404()

    data_dir = os.path.join(current_app.config['ABS_PATH'], 'static/datasets')

    ds_name = ds_model.name
    ds_dir = os.path.join(data_dir, ds_name)

    for image in ds_model.images.all():
        for rating in image.ratings.all():
            db.session.delete(rating)
        db.session.delete(image)
    db.session.delete(ds_model)

    rmtree(ds_dir)
    db.session.commit()

    flash(f'Dataset: {ds_name} was successfully deleted!',
          'success')
    return redirect(url_for('main.dashboard'))


@bp.route('/export-ratings', methods=['GET', 'POST'])
@bp.route('/export-ratings/<dataset>', methods=['GET', 'POST'])
@login_required
def export_ratings(dataset=None):
    """Page to configure and download a report of ratings."""
    form = ExportRatingsForm()
    form.dataset.choices = [ds.name for ds in Dataset.query.order_by('name')]

    not_subs, not_sess, not_comms = False, False, False
    if dataset is not None:
        ds_model = Dataset.query.filter_by(name=dataset).first_or_404()
        file_name = f'{ds_model.name}'

        subs = [i.subject for i in ds_model.images.all()]
        not_subs = (subs.count(None) == len(subs))
        sess = [i.session for i in ds_model.images.all()]
        not_sess = (sess.count(None) == len(sess))
        comments = [i.comment for i in
                    ds_model.
                    images.
                    join(Ratings).
                    add_columns(Ratings.comment).
                    all()]
        not_comms = (comments.count("") == len(comments))

    if form.validate_on_submit():
        query = Ratings.query.\
            join(Image).\
            filter(Image.dataset_id == ds_model.id).\
            order_by(Image.id.asc()).\
            add_columns(Image.name, Ratings.rating)
        keys = ['Image']
        if form.col_sub.data:
            query = query.add_columns(Image.subject)
            keys.append('Subject')
        if form.col_sess.data:
            query = query.add_columns(Image.session)
            keys.append('Session')
        if form.col_rater.data:
            query = query.join(Rater).add_columns(Rater.username)
            keys.append('Rater')
        keys.append('Rating')
        if form.col_comment.data:
            query = query.add_columns(Ratings.comment)
            keys.append('Comment')
        if form.col_timestamp.data:
            query = query.add_columns(Ratings.timestamp)
            keys.append('Date')
        if int(form.rater_filter.data):
            query = query.filter(Ratings.rater_id == current_user.id)
            file_name = f'{file_name}_{current_user.username}'

        ratings = []
        rating_codes = {0: 'Pending', 1: 'Pass', 2: 'Warning', 3: 'Fail'}
        for rating in query.all():
            rating_dict = {**dict.fromkeys(keys, None)}
            rating_dict['Image'] = rating.name
            rating_dict['Rating'] = rating_codes[rating.rating]
            if 'Subject' in rating_dict:
                rating_dict['Subject'] = rating.subject
            if 'Session' in rating_dict:
                rating_dict['Session'] = rating.session
            if 'Rater' in rating_dict:
                rating_dict['Rater'] = rating.username
            if 'Comment' in rating_dict:
                rating_dict['Comment'] = rating.comment
            if 'Date' in rating_dict:
                rating_dict['Date'] = rating.timestamp.isoformat() + 'Z'
            ratings.append(rating_dict)

        path = os.path.join(current_app.config['ABS_PATH'], 'static/reports')
        if not os.path.isdir(path):
            os.makedirs(path)

        if form.file_type.data == "CSV":
            file = ('static/reports/'
                    f'{file_name}_{datetime.now().date().isoformat()}.csv')
            with open(f'app/{file}', 'w', newline='') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=keys)
                writer.writerows(ratings)
        else:
            file = ('static/reports/'
                    f'{file_name}_{datetime.now().date().isoformat()}.json')
            with open(f'app/{file}', 'w', newline='') as json_file:
                json.dump(ratings, json_file, indent=4)
        return send_file(file, as_attachment=True)
    return render_template('export_ratings.html', form=form, dataset=dataset,
                           nsub=not_subs, nsess=not_sess, ncomms=not_comms,
                           title='Downlad Ratings')
