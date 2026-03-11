from flask import Blueprint, render_template


design_system_bp = Blueprint("design_system", __name__)


@design_system_bp.get("/design-system/homeschool")
def homeschool_design_system():
    return render_template("design_system_homeschool.html")
