"""
Qrater: Routes.

Module with different HTML routes for the webapp.
"""

import os
import re
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import (render_template, flash, redirect, url_for, request,
                   current_app, g)
from flask_login import current_user, login_required
from app import db
from app.upload import allowed_file
from app.main.forms import SearchForm, UploadDatasetForm
from app.models import Rater, Dataset, Image
from app.main import bp


@bp.before_app_request
def before_request():
    """Record time of rater's last activity."""
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        g.search_form = SearchForm()


@bp.route('/search')
@login_required
def search():
    """Search view function."""
    if not g.search_form.validate():
        return redirect(url_for('main.explore'))
    # page = request.args.get('page', 1, type=int)
    # posts, total = Post.search(g.search_form.q.data, page,
                               # current_app.config['POSTS_PER_PAGE'])
    # next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1) \
        # if total > page * current_app.config['POSTS_PER_PAGE'] else None
    # prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) \
        # if page > 1 else None
    # return render_template('search.html', title='Search', posts=posts,
                           # next_url=next_url, prev_url=prev_url)


@bp.route("/", methods=['GET', 'POST'])
@bp.route("/index", methods=['GET', 'POST'])
@login_required
def index():
    """Construct the landing page."""
    # if Dataset.query.first() is None:
        # return redirect(url_for('main.upload_dataset'))

    # page = request.args.get('page', 1, type=int)
    # posts = current_user.followed_posts().paginate(
        # page, current_app.config['POSTS_PER_PAGE'], False)
    # next_url = url_for('main.index', page=posts.next_num) \
        # if posts.has_next else None
    # prev_url = url_for('main.index', page=posts.prev_num) \
        # if posts.has_prev else None
    return render_template('index.html', title='Home')
                           # form=form,
                           # posts=posts.items, next_url=next_url,
                           # prev_url=prev_url)


@bp.route('/upload_dataset', methods=['GET', 'POST'])
@login_required
def upload_dataset():
    """Page to upload new dataset of MRI."""
    form = UploadDatasetForm()
    if request.method == 'POST':
        files = request.files.getlist(form.dataset.name)
        savedir = os.path.join(current_app.config['UPLOAD_FOLDER'],
                               'datasets', form.dataset_name.data)

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
                img = Image(name=bname, path=fpath, extension=ext,
                            dataset=dataset)
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
                imgs.append(img)
                # db.session.add(img)
            else:
                for img in imgs:
                    os.remove(img.path)
                db.session.delete(dataset)
                db.session.commit()
                flash(f'.{ext} is not a supported filetype', category='error')
                return redirect(request.url)
        for img in imgs:
            db.session.add(img)
            db.session.commit()
        flash('File(s) successfully uploaded!', category='success')
        return redirect(url_for('main.index'))
    return render_template('upload_dataset.html', form=form,
                           title='Upload Dataset')
