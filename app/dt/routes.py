"""
Qrater DataTables.

Module with blueprint specific routes
"""

from flask import jsonify, request, render_template
from datatables import ColumnDT, DataTables
from app.models import db, Dataset, Image, Ratings
from app.dt import bp


@bp.route('/datatable/<dataset>')
def datatable(dataset):
    """List a table with the images and their ratings."""
    # Figure out how to send Dataset
    ds_mod = Dataset.query.filter_by(name=dataset).first_or_404()

    subs = [i.subject for i in ds_mod.images.all()]
    sub_labs = (subs.count(None) != len(subs))

    sess = [i.session for i in ds_mod.images.all()]
    sess_labs = (sess.count(None) != len(sess))

    return render_template("dt/datatable.html",
                           DS=ds_mod, sub_labs=sub_labs, sess_labs=sess_labs)


@bp.route('/data/<dset_id>/<subs>/<sess>')
def data(dset_id, subs, sess):
    """Return server side data for datatable."""

    columns = [
        ColumnDT(Image.name),
        ColumnDT(Ratings.rating),
        ColumnDT(Ratings.timestamp),
    ]

    # Check if there are sess labels
    if sess == "True":
        columns.insert(1, ColumnDT(Image.session))

    # Check if there are sub labels
    if subs == "True":
        columns.insert(1, ColumnDT(Image.subject))

    query = db.session.query().\
        select_from(Image).\
        join(Ratings, isouter=True).\
        filter(Image.dataset_id == dset_id)

    params = request.args.to_dict()

    rowTable = DataTables(params, query, columns)
    return jsonify(rowTable.output_result())
