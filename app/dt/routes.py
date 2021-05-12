"""
Qrater DataTables.

Module with blueprint specific routes
"""

from flask import jsonify, request, render_template
from flask_login import current_user
from sqlalchemy import or_
from datatables import ColumnDT, DataTables
from app.models import db, Dataset, Image, Ratings, Rater
from app.dt import bp


@bp.route('/datatable/<dataset>')
def datatable(dataset):
    """List a table with the images and their ratings."""
    # Figure out how to send Dataset
    ds_mod = Dataset.query.filter_by(name=dataset).first_or_404()
    all_raters = request.args.get('all_raters', 0, type=int)
    only_ratings = request.args.get('only_ratings', 0, type=int)

    subs = [i.subject for i in ds_mod.images.all()]
    sub_labs = (subs.count(None) != len(subs))

    sess = [i.session for i in ds_mod.images.all()]
    sess_labs = (sess.count(None) != len(sess))

    return render_template("dt/datatable.html", DS=ds_mod,
                           all_raters=all_raters, only_ratings=only_ratings,
                           sub_labs=int(sub_labs), sess_labs=int(sess_labs))


@bp.route('/data/<int:dset_id>/<int:subject>/<int:session>/<int:only_ratings>')
def data(dset_id, subject, session, only_ratings=0):
    """Return server side data for datatable."""
    all_raters = request.args.get('all_raters', 0, type=int)

    columns = [
        ColumnDT(Image.name),
        ColumnDT(Ratings.rating),
        ColumnDT(Ratings.timestamp),
    ]

    # If ALL_RATERS, add rater column
    columns.insert(2, ColumnDT(Rater.username))

    # Check if there are sess labels
    if session:
        columns.insert(1, ColumnDT(Image.session))

    # Check if there are sub labels
    if subject:
        columns.insert(1, ColumnDT(Image.subject))

    # Ratings query for single user (only ratings)
    if not only_ratings:
        query = db.session.query().\
            select_from(Image).\
            filter(Image.dataset_id == dset_id).\
            join(Ratings, isouter=True).\
            join(Rater, isouter=True)
    elif all_raters or current_user.is_anonymous:
        query = db.session.query().\
            select_from(Image).\
            filter(Image.dataset_id == dset_id,
                   Ratings.rating > 0).\
            join(Ratings).\
            join(Rater)
    else:
        query = db.session.query().\
            select_from(Image).\
            filter(Image.dataset_id == dset_id,
                   Ratings.rater == current_user,
                   Ratings.rating > 0).\
            join(Ratings).\
            join(Rater)

    params = request.args.to_dict()

    rowTable = DataTables(params, query, columns)
    return jsonify(rowTable.output_result())
