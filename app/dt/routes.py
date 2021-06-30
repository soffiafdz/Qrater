"""
Qrater DataTables.

Module with blueprint specific routes
"""

from flask import jsonify, request, render_template
from flask_login import current_user
from datatables import ColumnDT, DataTables
from app.models import db, Dataset, Image, Rating, Rater
from app.dt import bp


@bp.route('/datatable/<dataset>')
def datatable(dataset):
    """List a table with the images and their ratings."""
    # Figure out how to send Dataset
    ds_model = Dataset.query.filter_by(name=dataset).first_or_404()
    all_raters = request.args.get('all_raters', 0, type=int)
    only_ratings = request.args.get('only_ratings', 0, type=int)

    col_names = ['Type', 'Sub', 'Sess', 'Rating']
    columns = {**dict.fromkeys(col_names, None)}

    types = [i.imgtype for i in ds_model.images.all()]
    columns['Type'] = (types.count(None) != len(types))

    subs = [i.subject for i in ds_model.images.all()]
    columns['Sub'] = (subs.count(None) != len(subs))

    sess = [i.session for i in ds_model.images.all()]
    columns['Sess'] = (sess.count(None) != len(sess))

    ratings_lists = [i.ratings.all() for i in ds_model.images.all()]
    columns['Rating'] = (ratings_lists.count([]) != len(ratings_lists))

    return render_template("dt/datatable.html", DS=ds_model,
                           types=columns['Type'], subs=columns['Sub'],
                           sess=columns['Sess'], ratings=columns['Rating'],
                           all_raters=all_raters, only_ratings=only_ratings)


@bp.route('/data/<int:dset_id>/<int:type>/<int:subject>/' +
          '<int:session>/<int:ratings>/<int:only_ratings>')
def data(dset_id, type, subject, session, ratings, only_ratings=0):
    """Return server side data for datatable."""
    all_raters = request.args.get('all_raters', 0, type=int)

    columns = [
        ColumnDT(Image.name),
        ColumnDT(Rating.rating),
    ]

    # If there are ratings insert rating info
    if ratings:
        columns.insert(2, ColumnDT(Rater.username))
        columns.insert(3, ColumnDT(Rating.timestamp))

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
    if not only_ratings:
        query = db.session.query().\
            select_from(Image).\
            filter(Image.dataset_id == dset_id).\
            join(Rating, isouter=True).\
            join(Rater, isouter=True)
    elif all_raters or current_user.is_anonymous:
        query = db.session.query().\
            select_from(Image).\
            filter(Image.dataset_id == dset_id,
                   Rating.rating > 0).\
            join(Rating).\
            join(Rater)
    else:
        query = db.session.query().\
            select_from(Image).\
            filter(Image.dataset_id == dset_id,
                   Rating.rater == current_user,
                   Rating.rating > 0).\
            join(Rating).\
            join(Rater)

    params = request.args.to_dict()

    rowTable = DataTables(params, query, columns)
    return jsonify(rowTable.output_result())
