# VC Mastermind Virtuals Agent

VC Mastermind is an AI-driven agent that empowers venture capitalists to evaluate potential investments with speed and confidence.
By automating due diligence, it benchmarks startups against historically successful companies, highlighting success probability, red flags, and actionable recommendations.

# 🚀 Problem

Venture capitalists spend weeks of manual research gathering data, analyzing comparable companies, and identifying risks in early-stage startups. This process is slow, biased, and often based on intuition rather than data.

# 💡 Solution

VC Mastermind automates the due diligence process using AI and large-scale historical datasets.

✅ Comprehensive Analysis – Captures industry, size, products, and location to build a full profile of a startup.

✅ Fast & Objective – Automates research, delivering instant, unbiased insights.

✅ Data-Driven – Benchmarks startups against companies that were once in the same position, identifying proven success patterns and red flags.

# 🔄 Product Flow

Analyzing Proposal
The agent ingests a startup’s summary and converts it into a structured schema — extracting key details such as industry, location, and business model.

Gathering Data
Using trusted datasets (e.g., EDGAR, startup databases), the agent finds comparable companies and tracks their performance over time.

Generating Report
Benchmarks the target startup against successful companies at a similar stage and produces a clear report with:

Success probability

Potential red flags

Actionable recommendations

# 🛠 Tech Stack

Language: Python 3.12

Core Packages:

markdown_pdf – Report generation

google.generativeai – AI analysis

jsonschema – Data validation

python-dotenv – Secure API key management

acp_virtuals – Agent protocol integration

# ⚙️ Installation

Clone the repository and set up a virtual environment with Python 3.12:

git clone https://github.com/lucasnye/team_1_sample.git
** cd team_1_sample/examples/acp_base/self_evaluation **

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate   # On Mac/Linux
venv\Scripts\activate      # On Windows

# Install dependencies
pip install -r requirements.txt

# ▶️ Usage

Add your API keys to a .env file:

GENAI_API_KEY=your_key_here


Run the agent in two separate terminals:
python seller.py
python buyer.py


Input a startup proposal summary.

Receive a PDF report with insights, benchmarks, and recommendations.

# 🎯 Current Status

This is a hackathon prototype showcasing how AI can transform startup due diligence.
Future improvements include:

Expanding datasets beyond EDGAR

Interactive dashboards

Deeper financial projections

👥 Team

Built for NTU x Base Hackathon by Team 1.
