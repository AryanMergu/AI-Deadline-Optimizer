from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

app = Flask(__name__)
CORS(app)

# =========================
# GROQ CONFIG
# =========================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("❌ GROQ_API_KEY missing in .env")
    exit(1)

client = Groq(api_key=GROQ_API_KEY)

print("✅ Groq AI connected")

# =========================
# HELPERS
# =========================

def calculate_days_remaining(deadline_str):
    """Calculate days until deadline"""
    try:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        return max((deadline - today).days, 1)
    except:
        return 3


def analyze_task_complexity(desc):
    """Analyze task complexity using keywords"""
    desc = desc.lower()

    complex_kw = ['machine learning','ai','algorithm','data science','neural network','deep learning','research']
    medium_kw = ['coding','development','website','app','api','programming','design']
    simple_kw = ['essay','reading','summary','notes','study','assignment']

    if any(k in desc for k in complex_kw):
        return "Complex", 1.4
    elif any(k in desc for k in medium_kw):
        return "Medium", 1.2
    else:
        return "Simple", 1.1


# =========================
# AI GENERATION (FIXED)
# =========================

def generate_ai_plan(data):
    """Generate AI plan with detailed, specific tasks"""
    try:
        task_name = data.get("task_name", "").strip()
        task_desc = data.get("task_description", "").strip()
        deadline = data.get("deadline")
        hours = float(data.get("total_hours", 10))
        productive = data.get("productive_hours", "6:00 PM - 11:00 PM")

        if not task_name or not task_desc:
            return None, "Task name and description required"

        days = calculate_days_remaining(deadline)
        complexity, multiplier = analyze_task_complexity(task_desc)
        adj_hours = hours * multiplier
        per_day = adj_hours / days

        # Determine feasibility
        if per_day <= 3:
            feasibility = "Comfortable"
            risk = "Low"
        elif per_day <= 5:
            feasibility = "Tight"
            risk = "Medium"
        else:
            feasibility = "Critical"
            risk = "High"

        # Create detailed prompt
        prompt = f"""You are an expert productivity coach. Create a realistic day-by-day task breakdown for this specific project.

TASK INFORMATION:
- Task Name: {task_name}
- Full Description: {task_desc}
- Days Available: {days}
- Total Hours: {hours} (adjusted to {adj_hours:.1f} with {complexity} buffer)
- Hours Per Day: {per_day:.1f}
- Productive Hours: {productive}
- Complexity: {complexity}
- Feasibility: {feasibility}
- Risk: {risk}

INSTRUCTIONS:
Create {days} days of SPECIFIC tasks for "{task_name}".
Each task must be directly related to "{task_desc}".
DO NOT use generic placeholders - make every task concrete and actionable.

Return ONLY this JSON structure (no markdown, no extra text):

{{
  "overview": {{
    "total_days": {days},
    "hours_per_day": {per_day:.1f},
    "complexity": "{complexity}",
    "feasibility": "{feasibility}",
    "risk_level": "{risk}",
    "motivation": "1-2 sentences of encouragement specific to {task_name}"
  }},
  "daily_breakdown": [
    {{
      "day": 1,
      "date": "Day 1 (Today)",
      "focus": "Specific milestone for day 1 of {task_name}",
      "tasks": [
        {{
          "time": "7:00 PM - 8:30 PM",
          "task": "Concrete actionable task related to {task_desc}",
          "duration": "1.5 hrs",
          "priority": "High"
        }},
        {{
          "time": "8:30 PM - 10:00 PM",
          "task": "Another specific task for {task_name}",
          "duration": "1.5 hrs",
          "priority": "Medium"
        }}
      ],
      "tip": "Practical advice for day 1"
    }}
  ],
  "warnings": [
    "Specific warning based on {feasibility} feasibility and {risk} risk"
  ],
  "success_strategies": [
    "Strategy 1 specific to {task_name}",
    "Strategy 2 for completing {task_desc}",
    "Strategy 3 considering {productive} schedule"
  ]
}}

CRITICAL RULES:
1. Create EXACTLY {days} day objects in daily_breakdown
2. Each day needs 2-4 tasks that build toward completing "{task_name}"
3. Tasks must reference specific aspects of "{task_desc}"
4. Use time slots within {productive}
5. NO generic text like "Task description" or "Focus area"
6. Make it realistic and actionable"""

        # Call Groq API
        print(f"🤖 Calling Groq AI for: {task_name}")
        
        chat = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are a productivity expert. Create detailed, specific task breakdowns. Always return valid JSON with concrete actions, never use placeholders."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.6,
            max_tokens=2500
        )

        text = chat.choices[0].message.content.strip()
        print(f"📝 Received {len(text)} chars")

        # Extract JSON
        start = text.find("{")
        end = text.rfind("}") + 1

        if start == -1 or end == 0:
            print("❌ No JSON in response")
            return None, "AI did not return valid JSON"

        json_text = text[start:end]
        plan = json.loads(json_text)

        # Enforce correct overview values
        if "overview" not in plan:
            plan["overview"] = {}

        plan["overview"]["total_days"] = days
        plan["overview"]["hours_per_day"] = round(per_day, 1)
        plan["overview"]["complexity"] = complexity
        plan["overview"]["feasibility"] = feasibility
        plan["overview"]["risk_level"] = risk

        # Ensure arrays exist
        if "daily_breakdown" not in plan or not isinstance(plan["daily_breakdown"], list):
            plan["daily_breakdown"] = []
        if "warnings" not in plan or not isinstance(plan["warnings"], list):
            plan["warnings"] = []
        if "success_strategies" not in plan or not isinstance(plan["success_strategies"], list):
            plan["success_strategies"] = []

        print(f"✅ Generated {len(plan['daily_breakdown'])} days")

        return plan, None

    except json.JSONDecodeError as je:
        print(f"❌ JSON Error: {je}")
        return None, "AI returned invalid JSON. Please try again."

    except Exception as e:
        print(f"❌ Error: {e}")
        return None, str(e)


# =========================
# ROUTES
# =========================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/generate-plan", methods=["POST"])
def api_generate_plan():
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "No data received"
            }), 400

        print("\n" + "="*60)
        print(f"📥 Request: {data.get('task_name')}")
        print("="*60)

        plan, error = generate_ai_plan(data)

        if error:
            print(f"❌ {error}\n")
            return jsonify({
                "success": False,
                "error": error
            }), 400

        print("✅ Success\n")
        return jsonify({
            "success": True,
            "plan": plan
        }), 200

    except Exception as e:
        print(f"❌ API Error: {e}")
        return jsonify({
            "success": False,
            "error": "Server error"
        }), 500


@app.route("/api/analyze-complexity", methods=["POST"])
def api_analyze_complexity():
    try:
        data = request.get_json()
        desc = data.get("description", "")

        if not desc:
            return jsonify({
                "success": False,
                "error": "Description required"
            }), 400

        comp, mult = analyze_task_complexity(desc)
        buffer = int((mult - 1) * 100)

        return jsonify({
            "success": True,
            "complexity": comp,
            "time_multiplier": mult,
            "explanation": f"Task classified as {comp} complexity. Adding {buffer}% buffer time."
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/sample-data", methods=["GET"])
def api_sample_data():
    """Return sample input/output"""
    sample_input = {
        "task_name": "Build Machine Learning Model",
        "task_description": "Create ML model for student performance prediction with data preprocessing, feature engineering, model training, and evaluation",
        "deadline": (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d"),
        "total_hours": "25",
        "productive_hours": "7:00 PM - 11:00 PM"
    }

    sample_output = {
        "overview": {
            "total_days": 5,
            "hours_per_day": 7.0,
            "complexity": "Complex",
            "feasibility": "Critical",
            "risk_level": "High",
            "motivation": "This is ambitious but achievable with focused effort. Stay disciplined!"
        },
        "daily_breakdown": [
            {
                "day": 1,
                "date": "Day 1 (Today)",
                "focus": "Project Setup & Data Exploration",
                "tasks": [
                    {
                        "time": "7:00 PM - 8:30 PM",
                        "task": "Set up development environment and load dataset",
                        "duration": "1.5 hrs",
                        "priority": "High"
                    },
                    {
                        "time": "8:30 PM - 10:00 PM",
                        "task": "Perform exploratory data analysis and identify patterns",
                        "duration": "1.5 hrs",
                        "priority": "High"
                    },
                    {
                        "time": "10:00 PM - 11:00 PM",
                        "task": "Document findings and plan preprocessing steps",
                        "duration": "1 hr",
                        "priority": "Medium"
                    }
                ],
                "tip": "Take time to understand your data - it saves debugging hours later"
            },
            {
                "day": 2,
                "date": "Day 2",
                "focus": "Data Preprocessing & Feature Engineering",
                "tasks": [
                    {
                        "time": "7:00 PM - 8:30 PM",
                        "task": "Handle missing values and outliers",
                        "duration": "1.5 hrs",
                        "priority": "High"
                    },
                    {
                        "time": "8:30 PM - 10:00 PM",
                        "task": "Create new features and encode categorical variables",
                        "duration": "1.5 hrs",
                        "priority": "High"
                    },
                    {
                        "time": "10:00 PM - 11:00 PM",
                        "task": "Split data and normalize features",
                        "duration": "1 hr",
                        "priority": "Medium"
                    }
                ],
                "tip": "Save intermediate datasets as checkpoints"
            }
        ],
        "warnings": [
            "⚠️ Tight timeline with 7 hours/day required",
            "⚠️ ML projects often have unexpected debugging - build in buffer time"
        ],
        "success_strategies": [
            "✓ Work during peak hours (7-11 PM) without distractions",
            "✓ Use existing libraries (scikit-learn) instead of custom code",
            "✓ Test incrementally - don't wait until the end",
            "✓ Ask for help early if stuck",
            "✓ Document your code as you go"
        ]
    }

    return jsonify({
        "sample_input": sample_input,
        "sample_output": sample_output
    }), 200


# =========================
# RUN
# =========================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 AI DEADLINE PANIC OPTIMIZER")
    print("="*60)
    print("📍 Server: http://localhost:5000")
    print("🤖 AI: Groq (Llama 3.1)")
    print("✨ Ready!")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)