import os
import boto3
from flask import Flask, jsonify, request
from botocore.exceptions import ClientError
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

app = Flask(__name__)

# X-Ray
xray_recorder.configure(service="course-service")
XRayMiddleware(app, xray_recorder)

# AWS Region
REGION = os.environ.get("AWS_REGION", "ap-south-2")

# DynamoDB
dynamodb = boto3.resource("dynamodb", region_name=REGION)
courses_table = dynamodb.Table("krishna-course")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "course-service"
    }), 200


@app.route("/courses/<course_id>", methods=["GET"])
def get_course(course_id):
    response = courses_table.get_item(
        Key={
            "id": course_id
        }
    )

    item = response.get("Item")

    if not item:
        return jsonify({
            "error": "Course not found"
        }), 404

    return jsonify(item), 200


@app.route("/courses", methods=["GET"])
def list_courses():
    response = courses_table.scan()

    return jsonify(
        response.get("Items", [])
    ), 


@app.route("/courses", methods=["POST"])
def add_course():
    try:
        data = request.get_json()

        # Validation
        if not data or "id" not in data or "name" not in data:
            return jsonify({
                "error": "Missing required fields: id, name"
            }), 400

        course_id = data["id"]

        # Insert only if course does not already exist
        courses_table.put_item(
            Item=data,
            ConditionExpression="attribute_not_exists(id)"
        )

        return jsonify({
            "message": "Course added successfully",
            "course": data
        }), 201

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return jsonify({
                "error": f"Course '{course_id}' already exists"
            }), 409

        return jsonify({
            "error": str(e)
        }), 500

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=3000,
        debug=False
    )