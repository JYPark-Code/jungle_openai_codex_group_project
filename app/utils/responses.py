from flask import jsonify


def success_response(data=None, message="요청이 성공했습니다.", status=200):
    return jsonify(
        {
            "success": True,
            "message": message,
            "data": data or {},
        }
    ), status


def error_response(error_code: str, message: str, details=None, status=400):
    return jsonify(
        {
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
                "details": details or {},
            },
        }
    ), status
