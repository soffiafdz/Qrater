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
from app.main.forms import (UploadDatasetForm, EditDatasetForm, RatingForm,
                            ExportRatingsForm)
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
@bp.route("/dashboard_<int:all_raters>", methods=['GET', 'POST'])
def dashboard(all_raters=None):
    """Construct the landing page."""
    if all_raters is not None and all_raters > 1:
        abort(404)
    if Dataset.query.first() is None:
        return render_template('no_datasets.html', title='Dashboard',
                               rater=current_user)
    # keys = ["total", "pass", "pass100", "warning", "warning100", "fail",
    # "fail100", "pending"]
    n_imgs = defaultdict(list)
    for dataset in Dataset.query.all():
        imgs = dataset.images
        ntot = imgs.count()
        n_0 = imgs.filter_by(ratings=None)\
            .union(imgs.join(Ratings).filter_by(rating=0)).count()
        n_1 = imgs.join(Ratings).filter_by(rating=1).count()
        n_2 = imgs.join(Ratings).filter_by(rating=2).count()
        n_3 = imgs.join(Ratings).filter_by(rating=3).count()
        n_imgs['total'].append(ntot)
        n_imgs['pending'].append(n_0)
        n_imgs['pass'].append(n_1)
        n_imgs['warning'].append(n_2)
        n_imgs['fail'].append(n_3)
        n_imgs['pass100'].append(round(n_1 / ntot * 100))
        n_imgs['warning100'].append(round(n_2 / ntot * 100))
        n_imgs['fail100'].append(round(n_3 / ntot * 100))
        print(n_imgs)
    return render_template('dashboard.html', title='Dashboard',
                           Image=Image, Ratings=Ratings,
                           datasets=Dataset.query.all(),
                           n_imgs=n_imgs)


@bp.route('/<dataset>', methods=['GET', 'POST'])
@bp.route('/<dataset>/filter-<int:r_filter>', methods=['GET', 'POST'])
@login_required
def rate(dataset, r_filter=None):
    """Page to view images and rate them."""
    DS = Dataset.query.filter_by(name=dataset).first_or_404()
    page = request.args.get('page', 1, type=int)
    if r_filter is None:
        imgs = DS.images.order_by(Image.id.asc()).paginate(page, 1, False)
    elif r_filter == 0:
        unrated = DS.images.filter_by(ratings=None)
        pending = DS.images.join(Ratings).filter_by(rating=r_filter)
        imgs = unrated.union(pending).order_by(Image.id.asc()).paginate(
            page, 1, False)
    elif r_filter < 4:
        imgs = DS.images.join(Ratings).filter_by(rating=r_filter).order_by(
            Image.id.asc()).paginate(page, 1, False)
    else:
        flash('Invalid filtering; Showing all images...', 'danger')
        return redirect(url_for('main.rate', dataset=dataset))
    if not imgs.items:
        flash('Filter ran out of images in filter; Showing all images...',
              'info')
        return redirect(url_for('main.rate', dataset=dataset))
    path = imgs.items[0].path.replace("app/static/", "")
    form = RatingForm()
    if form.validate_on_submit():
        img = imgs.items[0]
        img.set_rating(user=current_user, rating=form.rating.data)
        img.set_comment(user=current_user, comment=form.comment.data)
        return redirect(request.url)
    return render_template('rate.html', DS=DS, form=form, imgs=imgs, pag=True,
                           img_path=(path),
                           img_name=imgs.items[0].name,
                           comment=imgs.items[0].comment_by_user(current_user),
                           rating=imgs.items[0].rating_by_user(current_user))


@bp.route('/<dataset>/<image>', methods=['GET', 'POST'])
@login_required
def rate_img(dataset, image):
    """Page to view a single image and rate it."""
    DS = Dataset.query.filter_by(name=dataset).first_or_404()
    img = DS.images.filter_by(name=image).first_or_404()
    path = img.path.replace("app/static/", "")
    form = RatingForm()
    if form.validate_on_submit():
        img.set_rating(user=current_user, rating=form.rating.data)
        img.set_comment(user=current_user, comment=form.comment.data)
        return redirect(request.url)
    return render_template('rate.html', DS=DS, form=form, pag=False,
                           img_path=(path), img_name=img.name, filter=image,
                           comment=img.comment_by_user(current_user),
                           rating=img.rating_by_user(current_user))


@bp.route('/upload-dataset', methods=['GET', 'POST'])
@login_required
def upload_dataset():
    """Page to upload new dataset of MRI."""
    form = UploadDatasetForm()
    if form.validate_on_submit():
        files = request.files.getlist(form.dataset.name)
        savedir = os.path.join('app/static/datasets', form.dataset_name.data)

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


@bp.route('/edit-dataset', methods=['GET', 'POST'])
@bp.route('/edit-dataset/<dataset>', methods=['GET', 'POST'])
@login_required
def edit_dataset(dataset=None):
    """Page to edit an existing dataset of MRI."""
    if dataset is not None:
        ds_model = Dataset.query.filter_by(name=dataset).first_or_404()

    form = EditDatasetForm()
    form.dataset.choices = [ds.name for ds in Dataset.query.order_by('name')]

    test_names = {}
    for ds in Dataset.query.all():
        test_names[ds.name] = [img.name for img in ds.images.limit(5).all()]

    changes = False
    if form.validate_on_submit():
        print('First Pass')
        if form.new_name.data and form.new_name.data != ds_model.name:
            if Dataset.query.filter_by(name=form.new_name.data).first() \
                    is not None:
                flash((f'A Dataset named "{form.new_name.data}" '
                      'already exists. Please choose another name'),
                      'danger')
                return redirect(request.url)
            os.rename(os.path.join('app/static/datasets', ds_model.name),
                      os.path.join('app/static/datasets', form.new_name.data))
            for img in ds_model.images.all():
                img.path = img.path.replace(ds_model.name, form.new_name.data)
                db.session.add(img)
            ds_model.name = form.new_name.data
            db.session.add(ds_model)
            db.session.commit()
            changes = True

        files = request.files.getlist(form.imgs_to_upload.name)
        if files[0].filename != "":
            savedir = os.path.join('app/static/datasets', ds_model.name)
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

        if form.sub_regex.data or form.sess_regex.data:
            for img in ds_model.images.all():
                if form.sub_regex.data:
                    pattern = form.sub_regex.data
                    result = re.search(pattern, img.name)
                    if result:
                        img.subject = result.group()
                if form.sess_regex.data:
                    pattern = form.sess_regex.data
                    result = re.search(pattern, img.name)
                    if result:
                        img.session = result.group()
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
    ds_name = ds_model.name
    ds_dir = os.path.join('app/static/datasets', ds_name)

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

        path = 'app/static/reports'
        if not os.path.isdir(path):
            os.makedirs(path)

        if form.file_type.data == "CSV":
            file = ('static/reports/'
                    f'{file_name}_{datetime.now().date().isoformat()}.csv')
            with open(f'app/{file}', 'w', newline='') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=keys)
                writer.writeheader
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
