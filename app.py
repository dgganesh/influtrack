from flask import Flask, request, jsonify
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from bson import ObjectId
from flask import render_template
from collections import defaultdict

# Load environment variables
load_dotenv()

app = Flask(__name__)

# MongoDB Connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)

db = client["influencer_db"]
campaigns_collection = db["campaigns"]
expenses_collection = db["expenses"]

@app.route('/')
def home():
    return "Influencer Tracker Backend Running 🚀"


# 🔥 CREATE CAMPAIGN API
@app.route('/add_campaign', methods=['POST'])
def add_campaign():
    data = request.json

    campaign = {
        "name": data.get("name"),
        "brand": data.get("brand"),
        "platform": data.get("platform"),
        "status": data.get("status", "planned"),
        "payment_status": data.get("payment_status", "pending"),
        "amount": int(data.get("amount", 0)),
        "due_date": data.get("due_date")
    }

    campaigns_collection.insert_one(campaign)

    return jsonify({"message": "Campaign added successfully"}), 201

# 🔍 GET ALL CAMPAIGNS
@app.route('/get_campaigns', methods=['GET'])
def get_campaigns():
    campaigns = []

    for campaign in campaigns_collection.find({"status": {"$ne": "completed"}}):
        campaign["_id"] = str(campaign["_id"])  # convert ObjectId to string
        campaigns.append(campaign)

    return jsonify(campaigns), 200

# ✏️ UPDATE CAMPAIGN
@app.route('/update_campaign/<campaign_id>', methods=['PUT'])
def update_campaign(campaign_id):
    data = request.json

    update_fields = {}

    if "status" in data:
        update_fields["status"] = data["status"]

    if "payment_status" in data:
        update_fields["payment_status"] = data["payment_status"]

    if "amount" in data:
        update_fields["amount"] = data["amount"]

    campaigns_collection.update_one(
        {"_id": ObjectId(campaign_id)},
        {"$set": update_fields}
    )

    return jsonify({"message": "Campaign updated successfully"}), 200

# 🖥️ DASHBOARD UI
@app.route('/dashboard')
def dashboard():
    campaigns = []

    for campaign in campaigns_collection.find():
        campaign["_id"] = str(campaign["_id"])

        # 🔥 Normalize status
        status = campaign.get("status", "").strip().lower()

        # ❌ Skip completed campaigns
        if status == "completed":
            continue

        # Expenses logic
        expenses_cursor = expenses_collection.find({"campaign_id": campaign["_id"]})

        expenses = []
        total_expense = 0

        for exp in expenses_cursor:
            exp["_id"] = str(exp["_id"])
            amount = int(exp.get("amount", 0))
            total_expense += amount
            expenses.append(exp)

        campaign["total_expense"] = total_expense
        campaign["expenses"] = expenses

        campaigns.append(campaign)

    return render_template("index.html", campaigns=campaigns)

# 💰 ADD EXPENSE
@app.route('/add_expense', methods=['POST'])
def add_expense():
    data = request.json

    expense = {
        "campaign_id": data.get("campaign_id"),
        "title": data.get("title"),
        "amount": int(data.get("amount", 0)),
        "date": data.get("date")
    }

    expenses_collection.insert_one(expense)

    return jsonify({"message": "Expense added successfully"}), 201

@app.route('/completed')
def completed_campaigns():
    campaigns = []

    for campaign in campaigns_collection.find():
        campaign["_id"] = str(campaign["_id"])

        status = campaign.get("status", "").strip().lower()

        # ✅ Only include completed
        if status != "completed":
            continue

        expenses_cursor = expenses_collection.find({"campaign_id": campaign["_id"]})

        total_expense = 0
        for exp in expenses_cursor:
            total_expense += int(exp.get("amount", 0))

        campaign["total_expense"] = total_expense

        campaigns.append(campaign)

    return render_template("completed.html", campaigns=campaigns)

@app.route('/reports')
def reports():
    monthly_data = defaultdict(lambda: {
        "income": 0,
        "expense": 0
    })

    for campaign in campaigns_collection.find():
        status = campaign.get("status", "").strip().lower()

        # ✅ Only completed campaigns
        if status != "completed":
            continue

        campaign_id = str(campaign["_id"])

        # 🧠 Extract month from date
        date = campaign.get("due_date", "")
        month = date[:7]  # "2026-03"

        # 💰 Add income
        income = int(campaign.get("amount", 0))
        monthly_data[month]["income"] += income

        # 💸 Add expenses
        expenses_cursor = expenses_collection.find({"campaign_id": campaign_id})

        for exp in expenses_cursor:
            monthly_data[month]["expense"] += int(exp.get("amount", 0))

    # 🧾 Convert to list for template
    reports_list = []

    for month, data in monthly_data.items():
        reports_list.append({
            "month": month,
            "income": data["income"],
            "expense": data["expense"],
            "profit": data["income"] - data["expense"]
        })

    # 🔥 Sort by latest month first
    reports_list.sort(key=lambda x: x["month"], reverse=True)

    return render_template("reports.html", reports=reports_list)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
