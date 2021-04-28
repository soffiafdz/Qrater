"""
Qrater: Routes.

Module with different HTML routes for the webapp.
"""

import os
import re
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import (render_template, flash, redirect, url_for, request,
                   current_app, g)
from flask_login import current_user, login_required
from app import db
from app.upload import allowed_file
from app.main.forms import (UploadDatasetForm, EditDatasetForm, EmptyForm,
                            RatingForm)
from app.models import Dataset, Image, Ratings
from app.main import bp


@bp.before_app_request
def before_request():
    """Record time of rater's last activity."""
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@bp.route("/", methods=['GET', 'POST'])
@bp.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    """Construct the landing page."""
    if Dataset.query.first() is None:
        return render_template('no_datasets.html', title='Dashboard',
                               rater=current_user)
    n_tot, npass, npass100, nwarn, nwarn100, nfail, nfail100, npend = \
        [], [], [], [], [], [], [], []
    for dataset in Dataset.query.all():
        imgs = dataset.images
        ntot = imgs.count()
        n_0 = imgs.filter_by(ratings=None)\
            .union(imgs.join(Ratings).filter_by(rating=0)).count()
        n_1 = imgs.join(Ratings).filter_by(rating=1).count()
        n_2 = imgs.join(Ratings).filter_by(rating=2).count()
        n_3 = imgs.join(Ratings).filter_by(rating=3).count()
        n_tot.append(ntot)
        npend.append(n_0)
        npass.append(n_1)
        nwarn.append(n_2)
        nfail.append(n_3)
        npass100.append(round(n_1 / ntot * 100))
        nwarn100.append(round(n_2 / ntot * 100))
        nfail100.append(round(n_3 / ntot * 100))
    return render_template('dashboard.html', title='Dashboard',
                           Image=Image, Ratings=Ratings,
                           datasets=Dataset.query.all(),
                           npend=npend, n_tot=n_tot,
                           npass=npass, npass100=npass100,
                           nwarn=nwarn, nwarn100=nwarn100,
                           nfail=nfail, nfail100=nfail100)


@bp.route('/<dataset>', methods=['GET', 'POST'])
@bp.route('/<dataset>/filter_<int:filter>', methods=['GET', 'POST'])
@login_required
def rate(dataset, filter=None):
    """Page to view images and rate them."""
    DS = Dataset.query.filter_by(name=dataset).first_or_404()
    page = request.args.get('page', 1, type=int)
    if filter is None:
        imgs = DS.images.order_by(Image.id.asc()).paginate(page, 1, False)
    elif filter == 0:
        unrated = DS.images.filter_by(ratings=None)
        pending = DS.images.join(Ratings).filter_by(rating=filter)
        imgs = unrated.union(pending).order_by(Image.id.asc()).paginate(
            page, 1, False)
    elif filter < 4:
        imgs = DS.images.join(Ratings).filter_by(rating=filter).order_by(
            Image.id.asc()).paginate(page, 1, False)
    else:
        flash('Invalid filtering; Showing all images...', 'danger')
        return redirect(url_for('main.rate', dataset=dataset))
    if not imgs.items:
        flash('Filter ran out of images in filter; Showing all images...',
              'info')
        return redirect(url_for('main.rate', dataset=dataset))
    # TODO: This changes DSET_PATH to static... FIX
    path = imgs.items[0].path.replace("app/static/", "")
    form = RatingForm()
    if form.validate_on_submit():
        img = imgs.items[0]
        img.set_rating(user=current_user, rating=form.rating.data)
        img.set_comment(user=current_user, comment=form.comment.data)
        return redirect(request.url)
    return render_template('rate.html', DS=DS, form=form, imgs=imgs, pag=True,
                           filter=filter, img_path=(path),
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
                           img_path=(path), img_name=img.name,
                           comment=img.comment_by_user(current_user),
                           rating=img.rating_by_user(current_user))

@bp.route('/upload_dataset', methods=['GET', 'POST'])
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
                flash(f'.{ext} is not a supported filetype', 'error')
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


@bp.route('/edit_dataset', methods=['GET', 'POST'])
@bp.route('/edit_dataset/<dataset>', methods=['GET', 'POST'])
@login_required
def edit_dataset(dataset=None):
    """Page to edit an existing dataset of MRI."""
    if dataset is not None:
        pass

    form = EditDatasetForm()
    form.dataset.choices = [(ds.id, ds.name) for ds in
                            Dataset.query.order_by('name')]
    changes = False
    if form.validate_on_submit():
        ds_model = Dataset.query.get(form.dataset)

        if ds_model.name != form.new_name.data:
            if Dataset.query.filter_by(name=form.new_name.data).first() \
                    is not None:
                flash((f'A Dataset named "{form.new_name.data}" '
                      'already exists. Please choose another name'),
                      'danger')
                return redirect(request.url)
            os.rename(os.path.join('app/static/datasets', ds_model.name),
                      os.path.join('app/static/datasets', form.new_name.data))
            ds_model.name = form.new_name.data
            db.session.add(ds_model)
            db.session.commit()
            changes = True

        files = request.files.getlist(form.imgs_to_upload.name)
        if files:
            savedir = os.path.join('app/static/datasets', form.new_name.data)
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
                    flash(f'.{ext} is not a supported filetype', 'error')
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
            flash(f'{ds_model.name} successfully edited!', category='success')
        return redirect(url_for('main.dashboard'))
    return render_template('edit_dataset.html', form=form,
                           title='Edit Dataset')
