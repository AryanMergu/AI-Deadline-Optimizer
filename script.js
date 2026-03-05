/**
 * AI Deadline Panic Optimizer - Production Frontend
 * @version 2.0.0
 */

// --- STATE MANAGEMENT ---
let currentPlanData = null;

// --- NAVIGATION SYSTEM ---
function navigateTo(sectionId) {
    const sections = ['landing', 'about', 'profile', 'task', 'output'];
    sections.forEach(id => {
        const el = document.getElementById(`${id}-section`);
        if (id === sectionId) {
            el.classList.add('active');
        } else {
            el.classList.remove('active');
        }
    });
    window.scrollTo(0, 0);
}

// --- UTILS ---
function safeGet(obj, path, fallback = 'N/A') {
    return path.split('.').reduce((acc, part) => acc && acc[part], obj) || fallback;
}

function sanitize(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// --- API ACTIONS ---

// 1. Load Sample Data
async function loadSampleData() {
    try {
        const response = await fetch('/api/sample-data');
        const data = await response.json();
        
        if (data.sample_input) {
            const si = data.sample_input;
            document.getElementById('task-name').value = si.task_name || '';
            document.getElementById('task-description').value = si.task_description || '';
            document.getElementById('deadline').value = si.deadline || '';
            document.getElementById('total-hours').value = si.total_hours || '';
            document.getElementById('productive-hours').value = si.productive_hours || '6:00 PM - 11:00 PM';
            alert("Sample data loaded! Review the details and click Generate Plan.");
        }
    } catch (err) {
        console.error("Error loading sample:", err);
    }
}

// 2. Analyze Complexity (Standalone)
async function analyzeComplexity() {
    const desc = document.getElementById('task-description').value;
    if (!desc) return alert("Enter a description first!");

    const feedbackBox = document.getElementById('complexity-feedback');
    feedbackBox.style.display = 'block';
    feedbackBox.innerHTML = "<em>Analyzing patterns...</em>";

    try {
        const res = await fetch('/api/analyze-complexity', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ description: desc })
        });
        const data = await res.json();
        feedbackBox.innerHTML = `
            <div class="card warning">
                <strong>Complexity detected: ${data.complexity || 'Medium'}</strong>
                <p>${data.explanation || 'Analyzed using NLP keywords.'}</p>
            </div>
        `;
    } catch (err) {
        feedbackBox.innerHTML = "Error analyzing complexity.";
    }
}

// 3. Main Plan Generation
document.getElementById('task-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // UI Transitions
    navigateTo('output');
    document.getElementById('loading-state').style.display = 'block';
    document.getElementById('results-content').style.display = 'none';

    const formData = {
        task_name: document.getElementById('task-name').value,
        task_description: document.getElementById('task-description').value,
        deadline: document.getElementById('deadline').value,
        total_hours: document.getElementById('total-hours').value,
        productive_hours: document.getElementById('productive-hours').value
    };

    try {
        const response = await fetch('/api/generate-plan', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(formData)
        });
        const data = await response.json();

        if (data.success && data.plan) {
            currentPlanData = data.plan;
            renderPlan(data.plan);
            document.getElementById('loading-state').style.display = 'none';
            document.getElementById('results-content').style.display = 'block';
        } else {
            throw new Error(data.error || "Generation failed.");
        }
    } catch (err) {
        alert("API Error: " + err.message);
        navigateTo('task');
    }
});

// --- UI RENDERING ---

function renderPlan(plan) {
    const overview = plan.overview || {};
    
    // Overview Cards
    document.getElementById('plan-overview').innerHTML = `
        <div class="metric-card">
            <span class="metric-val">${overview.total_days}</span>
            <span class="metric-label">Total Days</span>
        </div>
        <div class="metric-card">
            <span class="metric-val">${overview.hours_per_day}h</span>
            <span class="metric-label">Hours / Day</span>
        </div>
        <div class="metric-card">
            <span class="metric-val">${overview.complexity}</span>
            <span class="metric-label">Complexity</span>
        </div>
        <div class="metric-card">
            <span class="metric-val">${overview.feasibility}</span>
            <span class="metric-label">Feasibility</span>
        </div>
    `;

    document.getElementById('motivation-box').innerHTML = `<strong>💡 AI Coach:</strong> ${overview.motivation}`;

    // Warnings
    const warnArea = document.getElementById('warnings-area');
    warnArea.innerHTML = (plan.warnings || []).map(w => `<div class="message-box warning">⚠️ ${w}</div>`).join('');

    // Daily Breakdown
    const dailyContainer = document.getElementById('daily-breakdown-container');
    dailyContainer.innerHTML = (plan.daily_breakdown || []).map(day => `
        <div class="day-card">
            <div class="day-title">${day.date}</div>
            <p><strong>Focus:</strong> ${day.focus}</p>
            ${(day.tasks || []).map(t => `
                <div class="task-row">
                    <div>
                        <strong>${t.time}:</strong> ${t.task} (${t.duration})
                    </div>
                    <span class="priority-tag ${(t.priority || 'medium').toLowerCase()}">${t.priority}</span>
                </div>
            `).join('')}
            <div style="margin-top:10px; font-size: 0.9rem; color: #64748b italic;">Tip: ${day.tip}</div>
        </div>
    `).join('');

    // Strategies
    document.getElementById('strategies-container').innerHTML = (plan.success_strategies || []).map(s => `
        <div class="message-box success" style="margin-bottom:10px;">✅ ${s}</div>
    `).join('');
}

// --- PDF EXPORT FUNCTION ---
async function downloadPDF() {
    if (!currentPlanData) return;

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF('p', 'mm', 'a4');
    const element = document.getElementById('pdf-target');

    // Use html2canvas to capture the UI for high-fidelity PDF
    const canvas = await html2canvas(element, { scale: 2 });
    const imgData = canvas.toDataURL('image/png');
    
    const imgWidth = 190;
    const pageHeight = 295;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;
    let heightLeft = imgHeight;
    let position = 10;

    doc.setFontSize(18);
    doc.text(`Project: ${currentPlanData.overview.task_name || 'My AI Deadline Plan'}`, 10, 10);
    doc.addImage(imgData, 'PNG', 10, position, imgWidth, imgHeight);
    
    doc.save(`AI_Plan_${new Date().toISOString().slice(0,10)}.pdf`);
}

// --- INIT ---
document.addEventListener('DOMContentLoaded', () => {
    // Set min date to today
    const dt = new Date().toISOString().split('T')[0];
    const dInput = document.getElementById('deadline');
    if (dInput) dInput.min = dt;
});