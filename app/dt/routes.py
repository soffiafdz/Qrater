"""
Qrater DataTables.

Module with blueprint specific routes
"""

from flask import jsonify, request, render_template
from datatables import ColumnDT, DataTables
from app.models import db, Dataset, Image, Ratings
from app.dt import bp


@bp.route('/datatable')
def datatable():
    """List a table with the images and their ratings."""
    # Figure out how to send Dataset
    # For testing purposes now just use the first one
    dataset_id = Dataset.query.first().id
    return render_template("dt/datatable.html", dataset=dataset_id)


@bp.route('/data/<dataset>')
def data(dataset):
    """Return server side data for datatable."""

    columns = [
        ColumnDT(Image.name),
        ColumnDT(Ratings.rating),
        ColumnDT(Ratings.timestamp),
    ]

    query = db.session.query().\
        select_from(Image).\
        join(Ratings, isouter=True).\
        filter(Image.dataset_id == dataset)

    params = request.args.to_dict()

    rowTable = DataTables(params, query, columns)
    return jsonify(rowTable.output_result())
