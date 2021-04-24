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
    DS = Dataset.query.filter_by(name=dataset).first_or_404()
    return render_template("dt/datatable.html", DS=DS)


@bp.route('/data/<dset_id>')
def data(dset_id):
    """Return server side data for datatable."""

    columns = [
        ColumnDT(Image.name),
        ColumnDT(Ratings.rating),
        ColumnDT(Ratings.timestamp),
    ]

    query = db.session.query().\
        select_from(Image).\
        join(Ratings, isouter=True).\
        filter(Image.dataset_id == dset_id)

    params = request.args.to_dict()

    rowTable = DataTables(params, query, columns)
    return jsonify(rowTable.output_result())
