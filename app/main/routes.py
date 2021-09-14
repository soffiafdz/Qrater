"""
Qrater: Routes.

Module with different HTML routes for the webapp.
"""

import os
import csv
import json
from collections import defaultdict
from datetime import datetime
from flask import (render_template, flash, abort, redirect, url_for, request,
                   current_app, send_file, jsonify)
from flask_login import current_user, login_required
from app import db
from app.main.forms import RatingForm, ExportRatingsForm, ImportRatingsForm
from app.models import Dataset, Image, Rating, Rater, Notification
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

    # Show all public datasets / accesible datasets for the current user
    public_ds = Dataset.query.filter_by(private=False)
    datasets = public_ds if current_user.is_anonymous \
        else Dataset.query.\
        filter(Dataset.viewers.contains(current_user)).\
        union(public_ds)

    # Reroute to 'Welcome' landing page if there are no ACCESSIBLE Datasets
    if datasets.first() is None:
        return render_template('no_datasets.html', title='Welcome',
                               rater=current_user)

    n_imgs = defaultdict(list)
    for dataset in datasets:
        imgs = dataset.images
        ntot = imgs.count()
        if all_raters or current_user.is_anonymous:
            n_0 = imgs.join(Rating).filter_by(rating=0).\
                union(imgs.filter_by(ratings=None)).distinct().count()
            n_1 = imgs.join(Rating).filter_by(rating=1).distinct().count()
            n_2 = imgs.join(Rating).filter_by(rating=2).distinct().count()
            n_3 = imgs.join(Rating).filter_by(rating=3).distinct().count()
            n_r = sum((n_1, n_2, n_3))
        else:
            n_1 = imgs.join(Rating).filter_by(rating=1, rater=current_user)\
                .count()
            n_2 = imgs.join(Rating).filter_by(rating=2, rater=current_user)\
                .count()
            n_3 = imgs.join(Rating).filter_by(rating=3, rater=current_user)\
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
                           Image=Image, Rating=Rating, datasets=datasets,
                           all_raters=all_raters, n_imgs=n_imgs)


@bp.route('/rate/<name_dataset>', methods=['GET', 'POST'])
@login_required
def rate(name_dataset):
    """Page to view images and rate them."""
    # If dataset doesn't exist abort with 404
    dataset = Dataset.query.filter_by(name=name_dataset).first_or_404()

    # All raters
    all_raters = request.args.get('all_raters', 0, type=int)

    # Double check rater's access
    if not current_user.has_access(dataset):
        flash(f"You don't have access to {dataset.name}", 'danger')
        all_raters_string = "all_raters" if all_raters else None
        return redirect(url_for('main.dashboard',
                                all_raters_string=all_raters_string))

    # Static directory
    statics_dir = os.path.join(current_app.config['ABS_PATH'], 'static')

    # Dictionary with all possible filters
    filters = {
        "image": request.args.get('image', None, type=str),
        "rating": request.args.get('rating_filter', None, type=int),
        "type": request.args.get('type_filter', None, type=str),
        "subject": request.args.get('sub_filter', None, type=str),
        "session": request.args.get('sess_filter', None, type=str),
        "cohort": request.args.get('cohort_filter', None, type=str)
    }

    # INIT with all dataset's images
    imgs = dataset.images

    # Paging
    pagination, page = True, request.args.get('page', 1, type=int)

    # TODO apply subqueries to this mess...
    # TODO add an example to remember what I meant with 'subqueries'
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

    imgs = imgs.filter_by(cohort=filters["cohort"]) \
        if filters["cohort"] else imgs

    if filters["rating"] is None:
        # If no rating_filter, no need to do anything else
        pass
    elif all_raters:
        if filters["rating"] == 0:  # PENDING
            # Images without any rating saved
            unrated = imgs.filter_by(ratings=None)

            # Images marked 'PENDING' by any rater
            pending = imgs.join(Rating).filter_by(rating=filters["rating"])

            # QUERY: UNRATED + PENDING
            # Unless they have another rating
            imgs = pending.union(unrated).distinct()

        # For ANY other rating; just filter by rating...
        elif filters["rating"] < 4:
            imgs = imgs.join(Rating).\
                filter_by(rating=filters["rating"]).\
                distinct()

        else:   # If 'rating' is >=4, there's an ERROR, so abort w/404
            flash('Invalid filtering; Showing all images...', 'danger')
            return redirect(url_for('main.rate', all_raters=all_raters,
                                    name_dataset=name_dataset))
    else:
        # For single rater (current); filtering is more specific
        if filters["rating"] == 0:
            # Images with ratings from CURRENT_RATER (except pending)
            rated = imgs.join(Rating).filter(Rating.rater == current_user,
                                             Rating.rating > 0)
            rated = db.session.query(Image.id).\
                filter(Image.dataset == dataset).\
                join(Rating).\
                filter(Rating.rater == current_user, Rating.rating != 0).\
                subquery()

            # All images, except Rated
            imgs = imgs.filter(Image.id.not_in(rated))

        elif filters["rating"] < 4:
            # Images where rating BY CURR_RATER matches rating filter
            imgs = imgs.join(Rating).filter_by(rating=filters["rating"],
                                               rater=current_user)
        else:  # If 'rating' is >=4, there's an ERROR, so abort w/404
            flash('Invalid filtering; Showing all images...',
                  'danger')
            return redirect(url_for('main.rate', all_raters=all_raters,
                                    name_dataset=name_dataset))

    imgs = imgs.order_by(Image.name.asc()).paginate(page, 1, False) \
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
        db.session.commit()
        return redirect(request.url)

    return render_template('rate.html', DS=dataset, form=form, imgs=imgs,
                           pagination=pagination, all_ratings=all_ratings,
                           img_name=img.name, img_path=path, title=img.name,
                           filters=filters, filtering=filtering,
                           all_raters=all_raters,
                           comment=img.comment_by_user(current_user),
                           rating=img.rating_by_user(current_user))


@bp.route('/export-ratings', methods=['GET', 'POST'])
@bp.route('/export-ratings/<dataset>', methods=['GET', 'POST'])
@login_required
def export_ratings(dataset=None):
    """Page to configure and download a report of ratings."""
    form = ExportRatingsForm()
    public_ds = Dataset.query.filter_by(private=False)
    private_ds = Dataset.query.filter(Dataset.viewers.contains(current_user))
    form.dataset.choices = [ds.name for ds in public_ds.union(private_ds)]

    # All raters
    all_raters = request.args.get('all_raters', 0, type=int)

    not_subs, not_sess, not_cohorts, not_comms = False, False, False, False
    if dataset is not None:
        ds_model = Dataset.query.filter_by(name=dataset).first_or_404()
        file_name = f'{ds_model.name}'

        subs = [i.subject for i in ds_model.images.all()]
        not_subs = (subs.count(None) == len(subs))
        sess = [i.session for i in ds_model.images.all()]
        not_sess = (sess.count(None) == len(sess))
        cohorts = [i.cohort for i in ds_model.images.all()]
        not_cohorts = (cohorts.count(None) == len(cohorts))
        comments = [i.comment for i in
                    ds_model.
                    images.
                    join(Rating).
                    add_columns(Rating.comment).
                    all()]
        not_comms = (comments.count("") == len(comments))

    if form.validate_on_submit():
        query = Rating.query.\
            join(Image).\
            filter(Image.dataset_id == ds_model.id).\
            order_by(Image.id.asc()).\
            add_columns(Image.name, Rating.rating)
        # keys = ['Image']
        keys = []
        if form.col_image.data:
            keys.append('Image')
        if form.col_sub.data:
            query = query.add_columns(Image.subject)
            keys.append('Subject')
        if form.col_sess.data:
            query = query.add_columns(Image.session)
            keys.append('Session')
        if form.col_cohort.data:
            query = query.add_columns(Image.cohort)
            keys.append('Cohort')
        if form.col_rater.data:
            query = query.join(Rater).add_columns(Rater.username)
            keys.append('Rater')
        keys.append('Rating')
        if form.col_comment.data:
            query = query.add_columns(Rating.comment)
            keys.append('Comment')
        if form.col_timestamp.data:
            query = query.add_columns(Rating.timestamp)
            keys.append('Date')
        if int(form.rater_filter.data):
            query = query.filter(Rating.rater_id == current_user.id)
            file_name = f'{file_name}_{current_user.username}'
        else:
            file_name = f'{file_name}_all-raters'

        ratings = []
        rating_codes = {0: 'Pending', 1: 'Pass', 2: 'Warning', 3: 'Fail'}
        for rating in query.all():
            rating_dict = {**dict.fromkeys(keys, None)}
            # rating_dict['Image'] = rating.name
            if 'Image' in rating_dict:
                rating_dict['Image'] = rating.name
            if 'Cohort' in rating_dict:
                rating_dict['Cohort'] = rating.cohort
            if 'Subject' in rating_dict:
                rating_dict['Subject'] = rating.subject
            if 'Session' in rating_dict:
                rating_dict['Session'] = rating.session
            rating_dict['Rating'] = rating_codes[rating.rating]
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
                           nsub=not_subs, nsess=not_sess, ncohort=not_cohorts,
                           ncomms=not_comms, all_raters=all_raters,
                           title='Downlad Ratings')


@bp.route('/import-ratings', methods=['GET', 'POST'])
@bp.route('/import-ratings/<dataset>', methods=['GET', 'POST'])
@login_required
def import_ratings(dataset=None):
    """Page to upload a report of ratings."""
    form = ImportRatingsForm()
    public_ds = Dataset.query.filter_by(private=False)
    private_ds = Dataset.query.filter(Dataset.viewers.contains(current_user))
    form.dataset.choices = [ds.name for ds in public_ds.union(private_ds)]

    # All raters
    all_raters = request.args.get('all_raters', 0, type=int)

    if form.validate_on_submit():
        keys = []
        if form.col_image.data:
            keys.append('Image')
        if form.col_sub.data:
            keys.append('Subject')
        if form.col_sess.data:
            keys.append('Session')
        if form.col_cohort.data:
            keys.append('Cohort')
        if form.col_rater.data:
            keys.append('Rater')
        keys.append('Rating')
        if form.col_comment.data:
            keys.append('Comment')
        if form.col_timestamp.data:
            keys.append('Date')

    # TODO: COMLETE


@bp.route('/notifications', methods=['GET', 'DELETE'])
@login_required
def notifications():
    """Notifications implementation."""
    since = request.args.get('since', 0.0, type=float)
    notifications = current_user.notifications.\
        filter(Notification.timestamp > since).\
        order_by(Notification.timestamp.asc())

    # If DELETE method; delete a notification
    # Useful for cleaning after showing in browser
    if request.method == 'DELETE':
        notification_name = request.args.get('name', None, type=str)
        notification = current_user.notifications.\
            filter(Notification.name == notification_name).first()

        if notification:
            db.session.delete(notification)
            db.session.commit()
        return '', 204

    # If GET, return notifications by AJAX
    return jsonify([{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    } for n in notifications])
