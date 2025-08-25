from flask import Flask, render_template_string, request
from groq import Groq
from datetime import datetime
import re
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def basic_markdown(text):
    """Simple function to convert Markdown to HTML."""
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    text = re.sub(r'^\s*#\s+(.*)$', r'<h1>\1</h1>', text, flags=re.M)
    text = re.sub(r'^\s*##\s+(.*)$', r'<h2>\1</h2>', text, flags=re.M)
    text = re.sub(r'^\s*###\s+(.*)$', r'<h3>\1</h3>', text, flags=re.M)
    text = re.sub(r'^\s*-\s+(.*)$', r'<li>\1</li>', text, flags=re.M)
    text = re.sub(r'(<li>.*</li>)', r'<ul>\1</ul>', text, flags=re.S)
    text = text.replace('\n', '<br>')
    return text

# HTML template (unchanged from the previous update)
HTML_TEMPLATE = '''
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Health Monitoring System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons/font/bootstrap-icons.css" rel="stylesheet">
    <style>
      body { background-color: #f8f9fa; }
      .card { border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
      .form-card { padding: 20px; }
      .insight-card { background-color: #f8f9fa; border-radius: 10px; padding: 20px; }
      .insight-card h2 { color: #007bff; }
      .result-card { background: linear-gradient(135deg, #ffffff 0%, #e9f7ff 100%); border: 1px solid #e0e0e0; border-radius: 15px; padding: 20px; margin-top: 20px; box-shadow: 0 8px 20px rgba(0,0,0,0.1); transition: all 0.4s ease; }
      .result-card:hover { box-shadow: 0 12px 30px rgba(0,0,0,0.15); transform: translateY(-4px); }
      .btn:hover { transform: translateY(-5px) scale(1.05); box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
      .alert { margin-top: 10px; }
    </style>
  </head>
  <body>
    <div class="container my-5">
      <h1 class="text-center mb-4"><i class="bi bi-heart-pulse me-2"></i>Health Monitoring System</h1>
      <p class="text-center text-muted">Enter your health data and Groq API key for AI-powered analysis. For educational purposes only.</p>
      
      <form method="POST" class="card form-card shadow">
        <div class="mb-3">
          <label for="heart_rate" class="form-label">Heart Rate (bpm)</label>
          <input type="number" class="form-control" id="heart_rate" name="heart_rate" placeholder="e.g., 70" required>
        </div>
        <div class="mb-3">
          <label for="blood_pressure" class="form-label">Blood Pressure (mmHg, e.g., 120/80)</label>
          <input type="text" class="form-control" id="blood_pressure" name="blood_pressure" placeholder="e.g., 120/80" required>
        </div>
        <div class="mb-3">
          <label for="temperature" class="form-label">Temperature (°C)</label>
          <input type="number" step="0.1" class="form-control" id="temperature" name="temperature" placeholder="e.g., 36.6" required>
        </div>
        <div class="mb-3">
          <label for="api_key" class="form-label">Groq API Key</label>
          <input type="text" class="form-control" id="api_key" name="api_key" placeholder="Enter your Groq API key" required>
          <div class="form-text">Obtain your API key from <a href="https://console.groq.com/keys" target="_blank">Groq Console</a>. It is not stored.</div>
        </div>
        <button type="submit" class="btn btn-primary w-100">Get Health Analysis</button>
      </form>
      
      {% if error %}
        <div class="alert alert-danger">{{ error }}</div>
      {% endif %}
      
      {% if analysis %}
        <div class="card insight-card">
          <div class="card-header bg-success text-white">
            <h4 class="mb-0">AI-Powered Health Analysis</h4>
          </div>
          <div class="card-body result-card">
            {{ analysis|safe }}
          </div>
        </div>
        <div class="mt-4 text-center">
          <button type="button" class="btn btn-warning me-2" onclick="history.back()"><i class="bi bi-arrow-repeat"></i> Regenerate</button>
          <a href="/" class="btn btn-secondary"><i class="bi bi-house-door"></i> Back to Home</a>
        </div>
      {% endif %}
    </div>
    <footer class="text-center text-muted py-4">
      <p>Powered by Groq | Last updated: {{ current_time }}</p>
    </footer>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  </body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    context = {
        'current_time': current_time,
        'error': None,
        'analysis': None
    }

    if request.method == 'POST':
        heart_rate = request.form.get('heart_rate')
        blood_pressure = request.form.get('blood_pressure')
        temperature = request.form.get('temperature')
        api_key = request.form.get('api_key')

        if not all([heart_rate, blood_pressure, temperature, api_key]):
            context['error'] = "Please fill in all fields."
            return render_template_string(HTML_TEMPLATE, **context)

        try:
            # Validate input data (basic checks)
            heart_rate = float(heart_rate)
            if not (40 <= heart_rate <= 200):  # Reasonable range for heart rate
                raise ValueError("Heart rate should be between 40 and 200 bpm.")

            # Split blood pressure into systolic/diastolic
            bp_values = [int(x) for x in blood_pressure.split('/')]
            if len(bp_values) != 2 or not (40 <= bp_values[0] <= 200 and 30 <= bp_values[1] <= 120):
                raise ValueError("Blood pressure should be in format 'systolic/diastolic' (e.g., 120/80) with valid ranges.")

            temperature = float(temperature)
            if not (35.0 <= temperature <= 42.0):  # Reasonable range for body temperature
                raise ValueError("Temperature should be between 35.0°C and 42.0°C.")

            # Prepare data for Groq prompt
            health_data = f"Heart Rate: {heart_rate} bpm, Blood Pressure: {blood_pressure} mmHg, Temperature: {temperature}°C"
            
            # Use Groq API for analysis
            client = Groq(api_key=api_key)
            prompt = f"""
            You are a health monitoring AI. Based on the following health data:
            {health_data}
            
            Provide a brief analysis of the user's health status. Include whether the readings are within normal ranges (e.g., heart rate 60-100 bpm, blood pressure 90/60 to 120/80 mmHg, temperature 36.6-38.0°C) and suggest any potential concerns or recommendations. Keep it concise and professional.
            Note: This is for educational purposes only and not a medical diagnosis.
            """
            logger.debug(f"Sending prompt to Groq: {prompt}")
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=300
            )
            analysis = completion.choices[0].message.content.strip()
            context['analysis'] = basic_markdown(analysis)  # Convert to HTML using markdown function

        except ValueError as e:
            context['error'] = f"Invalid input: {str(e)}"
            logger.error(f"Validation error: {str(e)}")
        except groq.APIConnectionError as e:
            context['error'] = f"API connection error: {str(e)}. Check your internet connection or try again later."
            logger.error(f"API connection error: {str(e)}")
        except groq.AuthenticationError as e:
            context['error'] = f"Authentication error: {str(e)}. Please verify your Groq API key."
            logger.error(f"Authentication error: {str(e)}")
        except groq.APIStatusError as e:
            context['error'] = f"API status error (HTTP {e.status_code}): {e.response}. This might be a server issue or rate limit. Try again later."
            logger.error(f"API status error: {str(e)}")
        except Exception as e:
            context['error'] = f"Error generating analysis: {str(e)}. Please check your API key or try again later."
            logger.error(f"Unexpected error: {str(e)}")

        return render_template_string(HTML_TEMPLATE, **context)

    return render_template_string(HTML_TEMPLATE, **context)

if __name__ == '__main__':
    app.run(debug=True)