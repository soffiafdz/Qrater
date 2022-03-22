"""
Qrater: Routes.

Module with different HTML routes for the webapp.
"""

import os
import csv
import json
import pandas as pd
from pandas.errors import ParserError
from collections import defaultdict, OrderedDict
from datetime import datetime
from flask import (render_template, flash, abort, redirect, url_for, request,
                   current_app, send_file, jsonify)
from flask_login import current_user, login_required
from app import db
from app.main.forms import RatingForm, ExportRatingsForm, ImportRatingsForm
from app.data.exceptions import NoExtensionError, UnsupportedExtensionError
from app.data.functions import upload_file
from app.models import Dataset, Image, Rating, Rater, Precomment, Notification
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
        if not dataset.sharing and current_user.is_anonymous:
            n_0 = ntot
            n_1 = n_2 = n_3 = n_r = 0
        elif dataset.sharing and (all_raters or current_user.is_anonymous):
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

    # Double check sharing/all_raters
    all_raters = all_raters if dataset.sharing else 0

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
        "rater": request.args.get('rater_filter', None, type=str),
        "type": request.args.get('type_filter', None, type=str),
        "subject": request.args.get('sub_filter', None, type=str),
        "session": request.args.get('sess_filter', None, type=str),
        "cohort": request.args.get('cohort_filter', None, type=str)
    }

    # INIT with all dataset's images
    imgs = dataset.images

    # Unrated images (used for filtering later)
    unrated = imgs.filter_by(ratings=None)

    # Paging
    pagination, page = True, request.args.get('page', 1, type=int)
    prev = request.args.get('prev', 0, type=int)

    subquery = Image.query.join(Rating).filter(Image.dataset == dataset,
                                               Rating.rater == current_user)

    _, prev_img, prev_time = subquery.order_by(Rating.timestamp.desc()).\
        add_columns(Image.name, Rating.timestamp).first() \
        if subquery.first() else None, None, None

    # If last rating is younger than 3 minutes give option de undo
    back = 0 if not prev_time \
        else 1 if (datetime.utcnow() - prev_time).total_seconds() < 360 \
        else 0

    # TODO apply subqueries to this mess...
    # TODO add an example to remember what I meant with 'subqueries'
    if filters["image"]:
        # If there is an image filtering, just show the image
        # There is nothing else to do (filter, query, etc...)
        img = dataset.images.filter_by(name=filters["image"]).first_or_404()

        # No need of pagination (Only 1 image); REWRITE VAR
        pagination, page = False, None

    else:
        imgs = imgs.filter_by(imgtype=filters["type"]) \
            if filters["type"] else imgs

        imgs = imgs.filter_by(subject=filters["subject"]) \
            if filters["subject"] else imgs

        imgs = imgs.filter_by(session=filters["session"]) \
            if filters["session"] else imgs

        imgs = imgs.filter_by(cohort=filters["cohort"]) \
            if filters["cohort"] else imgs

        if filters["rating"] is not None or filters["rater"]:
            imgs = imgs.join(Rating)
            imgs = imgs.\
                filter(Rating.rater == Rater.query.filter_by(
                    username=filters["rater"]).first()) \
                if filters["rater"] else imgs

        if filters["rating"] is None:
            pass

        elif filters["rating"] == 0:
            if all_raters:
                # Images marked 'PENDING' by any rater
                pending = imgs.filter(Rating.rating == 0)

                # QUERY: UNRATED + PENDING
                # Unless they have another rating
                imgs = pending.union(unrated).distinct()
            else:
                # Images with ratings from CURRENT_RATER (except pending)
                # rated = imgs.filter(Rating.rater == current_user,
                #                   Rating.rating > 0)
                rated = db.session.query(Image.id).\
                    filter(Image.dataset == dataset).\
                    join(Rating).\
                    filter(Rating.rater == current_user, Rating.rating != 0).\
                    subquery()

                # All images, except Rated
                imgs = imgs.filter(Image.id.not_in(rated)).\
                    union(unrated).distinct()

        elif filters["rating"] < 4:
            if all_raters:
                imgs = imgs.filter(Rating.rating == filters["rating"]).\
                    distinct()
            else:
                imgs = imgs.filter(Rating.rating == filters["rating"],
                                   Rating.rater == current_user)

        else:
            flash('Invalid filtering; Showing all images...', 'danger')
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
    filtering = bool(filters["image"]
                     or filters["rating"]
                     or filters["rating"] == 0
                     or filters["type"]
                     or filters["subject"]
                     or filters["session"]
                     or filters["rater"])

    img_subratings = img.subratings_by_user(current_user)
    subratings_json = [{
        "id": s.id,
        "selected": s in img_subratings,
        "rating": s.rating,
        "keybinding": s.keybinding
    } for s in dataset.subratings]

    # Rating form
    form = RatingForm()
    if form.validate_on_submit():
        subratings_to_add, subratings_to_delete = [], []
        sr_data = [(Precomment.query.get(sr[0]), sr[1]) for sr in
                   [string.split("_") for string in
                    form.subratings.data.split("___")]]

        for sr in sr_data:
            if sr[0] and sr[1] == "true":
                subratings_to_add.append(sr[0])
            elif sr[0] and sr[1] == "false":
                subratings_to_delete.append(sr[0])

        img.set_rating(user=current_user, rating=form.rating.data,
                       comment=form.comment.data, subratings=subratings_list)
        db.session.commit()
        return redirect(request.url)

    return render_template('rate.html', DS=dataset, form=form, imgs=imgs,
                           pagination=pagination, all_ratings=all_ratings,
                           img_name=img.name, img_path=path, title=img.name,
                           filters=filters, filtering=filtering, prev=prev,
                           all_raters=all_raters, prev_img=prev_img, back=back,
                           subratings=dataset.subratings,
                           subratings_data=subratings_json,
                           rating=img.rating_by_user(current_user),
                           comment=img.comment_by_user(
                               current_user, add_subratings=False))


@bp.route('/export-ratings', methods=['GET', 'POST'])
@bp.route('/export-ratings/<dataset>', methods=['GET', 'POST'])
@login_required
def export_ratings(dataset=None):
    """Page to configure and download a report of ratings."""
    # TODO: Check if add imgtype
    columns = [["Image", 1, 0], ["Subject", 0, 0], ["Session", 0, 0],
               ["Cohort", 0, 0], ["Rater", 0, 0], ["Rating", 1, 0],
               ["Comments", 0, 0], ["Timestamp", 0, 0]]

    form = ExportRatingsForm()
    public_ds = Dataset.query.filter_by(private=False)
    private_ds = Dataset.query.filter(Dataset.viewers.contains(current_user))
    form.dataset.choices = [ds.name for ds in public_ds.union(private_ds)]
    # id, name, activated, read-only
    form.columns.choices = [[i, column[0], column[1], column[2]]
                            for i, column in enumerate(columns)]

    # All raters
    all_raters = request.args.get('all_raters', 0, type=int)

    not_subs, not_sess, not_cohorts, not_comms = False, False, False, False
    if dataset is not None:
        ds_model = Dataset.query.filter_by(name=dataset).first_or_404()
        file_name = f'{ds_model.name}'

        form.columns.choices[1][3] = 0 \
            if sum([bool([i.subject for i in ds_model.images])]) else 1

        form.columns.choices[2][3] = 0 \
            if sum([bool([i.session for i in ds_model.images])]) else 1

        form.columns.choices[3][3] = 0 \
            if sum([bool([i.cohort for i in ds_model.images])]) else 1

        comm = [bool(r.comment) for r in
                ds_model.images.join(Rating).add_columns(Rating.comment)]
        subr = [bool(r.subratings.all()) for r in
                Rating.query.join(Image).filter(Image.dataset == ds_model)]
        form.columns.choices[6][3] = 0 if (sum(comm) or sum(subr)) else 1

    if form.validate_on_submit():
        query = Rating.query.\
            join(Image).\
            filter(Image.dataset_id == ds_model.id).\
            order_by(Image.id.asc()).\
            add_columns(Image.name, Rating.rating)

        rating_dict = OrderedDict()
        col_order = [int(order) for order in form.order.data]
        for col_name in [[val[1] for val in form.columns.choices][order]
                         for order in col_order]:
            rating_dict[col_name] = None

        if "Subject" in rating_dict.keys():
            query = query.add_columns(Image.subject)

        if "Session" in rating_dict.keys():
            query = query.add_columns(Image.session)

        if "Cohort" in rating_dict.keys():
            query = query.add_columns(Image.cohort)

        if "Rater" in rating_dict.keys():
            query = query.join(Rater).add_columns(Rater.username)

        if "Comments" in rating_dict.keys():
            query = query.add_columns(Rating.comment)

        if "Timestamp" in rating_dict.keys():
            query = query.add_columns(Rating.timestamp)

        if int(form.rater_filter.data):
            query = query.filter(Rating.rater_id == current_user.id)
            file_name = f'{file_name}_{current_user.username}'
        else:
            file_name = f'{file_name}_all-raters'

        ratings = []
        rating_codes = {0: 'Pending', 1: 'Pass', 2: 'Warning', 3: 'Fail'}
        for rating in query.all():
            if "Image" in rating_dict.keys():
                rating_dict['Image'] = rating.name

            if "Subject" in rating_dict.keys():
                rating_dict['Subject'] = rating.subject

            if "Session" in rating_dict.keys():
                rating_dict['Session'] = rating.session

            if "Cohort" in rating_dict.keys():
                rating_dict['Cohort'] = rating.cohort

            if "Rating" in rating_dict.keys():
                rating_dict['Rating'] = rating_codes[rating.rating]

            if "Rater" in rating_dict.keys():
                rating_dict['Rater'] = rating.username

            if "Comments" in rating_dict.keys():
                rating_dict['Comments'] = rating.comment

            if "Timestamp" in rating_dict.keys():
                rating_dict['Timestamp'] = rating.timestamp.isoformat() + 'Z'

            ratings.append({k: v for k, v in rating_dict.items()})

        path = os.path.join(current_app.config['ABS_PATH'], 'static/reports')
        if not os.path.isdir(path):
            os.makedirs(path)

        if form.file_type.data == "CSV":
            file = ('static/reports/'
                    f'{file_name}_{datetime.now().date().isoformat()}.csv')
            with open(f'app/{file}', 'w', newline='') as csv_file:
                writer = csv.DictWriter(csv_file, rating_dict.keys())
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
    all_raters = request.args.get('all_raters', 0, type=int)
    public_ds = Dataset.query.filter_by(private=False)
    private_ds = Dataset.query.filter(Dataset.viewers.contains(current_user))
    form.dataset.choices = [ds.name for ds in public_ds.union(private_ds)]
    # TODO: Check if add imgtype
    rating_codes = {'Pending': 0, 'Pass': 1, 'Warning': 2, 'Fail': 3}

    column_choices = ["Image", "Subject", "Session", "Cohort", "Rater",
                      "Rating", "Comments", "Timestamp"]
    form.columns.choices = [(i, name) for i, name in enumerate(column_choices)]

    if dataset is not None:
        ds_model = Dataset.query.filter_by(name=dataset).first_or_404()

    path = os.path.join(current_app.config['ABS_PATH'], 'static/reports')
    if not os.path.isdir(path):
        os.makedirs(path)

    if form.validate_on_submit():
        filetype = form.file_type.data.lower()
        # Read file
        try:
            fpath = upload_file(form.file.data, path, [filetype])

        except NoExtensionError as error:
            flash(str(error), 'danger')
            return redirect(url_for('main.import_ratings', dataset=dataset,
                                    all_raters=all_raters))

        except UnsupportedExtensionError as error:
            flash(str(error), 'danger')
            return redirect(url_for('main.import_ratings', dataset=dataset,
                                    all_raters=all_raters))

        try:
            ratings = pd.read_json(fpath) if filetype == 'json' \
                else pd.read_csv(fpath, header=None)

        except ParserError as error:
            flash(f"Uploading error: {str(error)}", 'danger')
            return redirect(url_for('main.import_ratings', dataset=dataset,
                                    all_raters=all_raters))

        # Check number of columns matches options selected
        column_order = [int(order) for order in form.order.data]
        column_names = [[val[1] for val in form.columns.choices][order]
                        for order in column_order]

        selected = None

        # TODO: maybe add option for header in CSV?
        if filetype == 'json':
            # Check that all columns are capitalized
            if not all(name.istitle() for name in ratings.columns):
                ratings.columns = ratings.columns.str.title()

            set_file = set(ratings.columns)
            set_select = set(column_names)
            not_in_file = list(set_select - set_file)
            not_in_select = list(set_file - set_select)

            # Selected in menu but not in JSON file
            if not_in_file:
                flash(f"{len(not_in_file)} selected but not found in file: "
                      f"{not_in_file}", "danger")
                return redirect(url_for('main.import_ratings', dataset=dataset,
                                        all_raters=all_raters))

            # In JSON file, but not selected
            if not_in_select:
                flash(f"{len(not_in_select)} columns in file not loaded: "
                      f"{not_in_select}", "warning")

            # Selected and in JSON
            selected = list(set_select & set_file)

        # If CSV, then assign column names according to selection
        # Order will be according to column choices declared above
        else:
            # Check that column number and selection matches before assignment
            if len(column_names) != len(ratings.columns):
                flash(f"Selected columns: {len(column_names)} "
                      "don't match the number of columns in uploaded file: "
                      f"{len(ratings.columns)}. Check file and try again.",
                      'danger')
                return redirect(url_for('main.import_ratings', dataset=dataset,
                                        all_raters=all_raters))

            selected = ratings.columns = column_names

        # Parse data
        query = Image.query.filter_by(dataset=ds_model)
        rating = dict.fromkeys(column_choices, None)
        not_found, ambiguous, loaded = [], 0, 0

        for row in ratings.index:
            # Save value into rating dictionary
            for column in selected:
                rating[column] = ratings.at[row, column]

            # Find image:
            if rating["Image"]:
                subquery = query.filter_by(name=rating["Image"])
                # If no image by that name, go to next row
                if not subquery.first():
                    not_found.append(rating["Image"])
                    continue

            # More precise filtering
            image_filters = []
            for filter in ["Subject", "Session", "Cohort"]:
                val = rating[filter] if rating[filter] else None
                if isinstance(val, str):
                    image_filters.append(f"{filter}: {val}")
                    test = subquery.\
                        filter(getattr(Image, filter.lower()) == val)
                    subquery = test if test.first() else subquery

            # Ambiguity check: if more than one possible image, pass
            if not subquery.first():
                not_found.append("; ".join(image_filters))
                continue
            elif subquery.count() > 1:
                ambiguous += 1
                continue
            else:
                img = subquery.first()

            # Set Data: Rating; Comments; Timestamp; Rater
            # TODO: Add check if username doesn't exist
            rater = Rater.query.filter_by(username=rating["Rater"]).first() \
                if rating["Rater"] else current_user
            if not rater:
                image_filters.append(f"Rater: {rater}")
                not_found.append("; ".join(image_filters))
                continue

            rate_num = rating_codes[rating["Rating"].title()] \
                if isinstance(rating["Rating"], str) else rating["Rating"]

            if isinstance(rate_num, int):
                img.set_rating(user=rater, rating=rate_num,
                               timestamp=rating["Timestamp"])
            else:
                continue

            comment = rating["Comments"] if rating["Comments"] else None
            if isinstance(comment, str):
                img.set_rating(user=rater, comment=comment)

            db.session.commit()
            loaded += 1

        if not_found:
            n = len(not_found)
            if n < 5:
                flash(f"{n} images were not found: " + str(not_found),
                      "warning")
            else:
                flash(f"{n} images were not found.", "danger")

        if ambiguous:
            flash(f"{ambiguous} images were not loaded because more than "
                  "one image with that criteria was found.", "warning")

        if loaded:
            flash(f"{loaded} images' ratings were successfully loaded!",
                  "success")

        return redirect(url_for('main.dashboard', all_raters=all_raters))

    return render_template('import_ratings.html', form=form, dataset=dataset,
                           all_raters=all_raters, title='Upload Ratings')


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
