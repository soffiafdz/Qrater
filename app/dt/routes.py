"""
Qrater DataTables.

Module with blueprint specific routes
"""

from flask import jsonify, request, render_template, flash, redirect, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from datatables import ColumnDT, DataTables
from app.models import db, Dataset, Image, Rating, Rater
from app.dt import bp


@bp.route('/datatable/<dataset>')
@login_required
def datatable(dataset):
    """List a table with the images and their ratings."""
    # Figure out how to send Dataset
    ds_model = Dataset.query.filter_by(name=dataset).first_or_404()
    all_raters = request.args.get('all_raters', 0, type=int)
    only_ratings = request.args.get('only_ratings', 0, type=int)

    # Double check sharing ratings
    all_raters = all_raters if ds_model.sharing else 0

    # Double check rater's access
    if not current_user.has_access(ds_model):
        flash(f"You don't have access to {dataset.name}", 'danger')
        all_raters_string = "all_raters" if all_raters else None
        return redirect(url_for('main.dashboard',
                                all_raters_string=all_raters_string))

    col_names = ['Type', 'Sub', 'Sess', 'Cohort', 'Rating', 'Comment']
    columns = {**dict.fromkeys(col_names, None)}

    columns['Type'] = bool(sum([bool(i.imgtype) for i in ds_model.images]))
    columns['Sub'] = bool(sum([bool(i.subject) for i in ds_model.images]))
    columns['Sess'] = bool(sum([bool(i.session) for i in ds_model.images]))
    columns['Cohort'] = bool(sum([bool(i.cohort) for i in ds_model.images]))
    columns['Rating'] = bool(sum([bool(i.ratings.all())
                                  for i in ds_model.images]))
    comments = [bool(r.comment) for r in
                Rating.query.join(Image).filter(Image.dataset == ds_model)]
    subratings = [bool(r.subratings.all()) for r in
                  Rating.query.join(Image).filter(Image.dataset == ds_model)]
    columns['Comment'] = (sum(comments) or sum(subratings))

    return render_template("dt/datatable.html", DS=ds_model,
                           types=columns['Type'], subs=columns['Sub'],
                           sess=columns['Sess'], cohorts=columns['Cohort'],
                           ratings=columns['Rating'], comms=columns['Comment'],
                           all_raters=all_raters, only_ratings=only_ratings)


@bp.route('/data/<int:dset_id>/<int:type>/<int:subject>/' +
          '<int:session>/<int:cohort>/<int:ratings>/' +
          '<int:comments>/<int:only_ratings>')
def data(dset_id, type, subject, session, cohort, ratings, comments,
         only_ratings=0):
    """Return server side data for datatable."""
    all_raters = request.args.get('all_raters', 0, type=int)

    columns = [
        ColumnDT(Image.name),
        ColumnDT(Rating.rating),
    ]

    # If there are ratings insert rating info
    if ratings:
        columns.insert(2, ColumnDT(Rating.timestamp))
        # TODO Figure out how to insert subratings here
        if comments:
            columns.insert(2, ColumnDT(Rating.comment))
        if all_raters:
            columns.insert(2, ColumnDT(Rater.username))

    # Check if there are cohort labels
    if cohort:
        columns.insert(1, ColumnDT(Image.cohort))

    # Check if there are sess labels
    if session:
        columns.insert(1, ColumnDT(Image.session))

    # Check if there are sub labels
    if subject:
        columns.insert(1, ColumnDT(Image.subject))

    # Check if there are type labels
    if type:
        columns.insert(1, ColumnDT(Image.imgtype))

    # Ratings query for single user (only ratings)
    if all_raters or current_user.is_anonymous:
        query = db.session.query().\
            select_from(Image).\
            filter(Image.dataset_id == dset_id,
                   Rating.rating > 0).\
            join(Rating).\
            join(Rater) if only_ratings \
            else db.session.query().\
            select_from(Image).\
            filter(Image.dataset_id == dset_id).\
            join(Rating, isouter=True).\
            join(Rater, isouter=True)
    else:
        if only_ratings:
            query = db.session.query().\
                select_from(Image).\
                filter(Image.dataset_id == dset_id,
                       Rating.rater == current_user,
                       Rating.rating > 0).\
                join(Rating).\
                join(Rater)
        else:
            query = db.session.query().\
                select_from(Image).\
                filter(Image.dataset_id == dset_id,
                       or_(Rating.rater == current_user,
                           Rating.rater == None)).\
                join(Rating, isouter=True).\
                join(Rater, isouter=True)

    params = request.args.to_dict()

    rowTable = DataTables(params, query, columns)
    return jsonify(rowTable.output_result())
