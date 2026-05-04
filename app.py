import os
import boto3
from flask import Flask, jsonify, request
from botocore.exceptions import ClientError
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.flask.middleware import XRayMiddleware

app = Flask(__name__)

# X-Ray Configuration
xray_recorder.configure(service="course-service")
XRayMiddleware(app, xray_recorder)

# AWS Region
REGION = os.environ.get("AWS_REGION", "ap-south-2")

# DynamoDB Connection
dynamodb = boto3.resource("dynamodb", region_name=REGION)
courses_table = dynamodb.Table("krishna-course")


# Health Check API
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "course-service"
    }), 200


# Get All Courses
@app.route("/courses", methods=["GET"])
def list_courses():
    try:
        response = courses_table.scan()
        return jsonify(response.get("Items", [])), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# Get Course by ID
@app.route("/courses/<course_id>", methods=["GET"])
def get_course(course_id):
    try:
        response = courses_table.get_item(
            Key={"id": course_id}
        )

        item = response.get("Item")

        if not item:
            return jsonify({
                "error": "Course not found"
            }), 404

        return jsonify(item), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# Add New Course
@app.route("/courses", methods=["POST"])
def add_course():
    try:
        data = request.get_json()

        if not data or "id" not in data or "name" not in data or "credits" not in data:
            return jsonify({
                "error": "Missing required fields: id, name, credits"
            }), 400

        if not isinstance(data["credits"], int):
            return jsonify({
                "error": "credits must be an integer"
            }), 400

        course_id = data["id"]

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

        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=3000,
        debug=False
    )
