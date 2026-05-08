lucide.createIcons();

// 1. LOGIC CHUYỂN TAB (SQL Query <-> Database Schema)
const tabQuery = document.getElementById('tabQuery');
const tabSchema = document.getElementById('tabSchema');
const contentQuery = document.getElementById('contentQuery');
const contentSchema = document.getElementById('contentSchema');

tabQuery.onclick = () => { 
    tabQuery.classList.add('tab-active'); 
    tabSchema.classList.remove('tab-active'); 
    contentQuery.classList.remove('hidden'); 
    contentSchema.classList.add('hidden'); 
};

tabSchema.onclick = () => { 
    tabSchema.classList.add('tab-active'); 
    tabQuery.classList.remove('tab-active'); 
    contentSchema.classList.remove('hidden'); 
    contentQuery.classList.add('hidden'); 
};

// 2. HÀM XÓA DỮ LIỆU
function clearInput() {
    document.getElementById('sqlInput').value = '';
    document.getElementById('logContainer').innerHTML = '<p class="text-sm text-slate-400 italic">No activity yet.</p>';
    document.getElementById('statIssues').innerText = '0';
    document.getElementById('statIssues').className = 'text-3xl font-bold text-slate-400';
    document.getElementById('statSuggestions').innerText = '0';
}

// 3. LOGIC GỬI DỮ LIỆU TỚI API (QUAN TRỌNG NHẤT)
document.getElementById('validateBtn').addEventListener('click', async function() {
    const sql = document.getElementById('sqlInput').value;
    const schemaText = document.getElementById('schemaInput').value; 

    const selectedDialect = document.getElementById('dialectSelect').value;

    if(!sql) return alert("Vui lòng nhập câu lệnh SQL!");
    if(!schemaText) return alert("Vui lòng dán nội dung CREATE TABLE vào tab Database Schema!");
    
    const btn = this;
    const originalHTML = btn.innerHTML;
    btn.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>AI Fixing...</span>';
    lucide.createIcons();

    try {
        const response = await fetch('http://127.0.0.1:8000/api/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                sql: sql,
                schema_text: schemaText,
                dialect: selectedDialect
            })
        });

        const data = await response.json();

        // Cập nhật thống kê lỗi dựa trên Issue Count từ Backend
        const issueEl = document.getElementById('statIssues');
        issueEl.innerText = data.issues;
        issueEl.className = `text-3xl font-bold ${data.issues > 0 ? 'text-red-500' : 'text-emerald-500'}`;
        
        document.getElementById('statSuggestions').innerText = data.suggestions || 0;
        document.getElementById('statPassed').innerText = data.status === 'failed' ? '0' : '4';

        // Render Repair Logs với màu sắc động
        const logContainer = document.getElementById('logContainer');
        logContainer.innerHTML = '';

        data.logs.forEach(log => {
            let bgColor = 'bg-slate-50 border-slate-200';
            let icon = 'info';
            let iconColor = 'text-slate-400';

            if (log.includes('❌')) {
                bgColor = 'bg-red-50 border-red-100 shadow-sm';
                icon = 'alert-circle';
                iconColor = 'text-red-500';
            } else if (log.includes('🤖')) {
                bgColor = 'bg-blue-50 border-blue-100';
                icon = 'sparkles';
                iconColor = 'text-blue-500';
            } else if (log.includes('✅')) {
                // LOG THÀNH CÔNG CUỐI CÙNG (HIỆN MÀU XANH LÁ)
                bgColor = 'bg-emerald-50 border-emerald-300 border-2 shadow-md';
                icon = 'check-circle';
                iconColor = 'text-emerald-600';
            } else if (log.includes('🛑')) {
                bgColor = 'bg-orange-50 border-orange-200';
                icon = 'shield-alert';
                iconColor = 'text-orange-600';
            }

            logContainer.innerHTML += `
                <div class="flex items-start space-x-3 p-4 border ${bgColor} rounded-xl transition-all animate-in fade-in duration-500">
                    <i data-lucide="${icon}" class="w-5 h-5 ${iconColor} mt-0.5"></i>
                    <span class="text-xs font-mono text-slate-700 leading-relaxed font-bold break-words">${log}</span>
                </div>
            `;
        });

    } catch (error) {
        alert("Lỗi kết nối Backend! Hãy chắc chắn bạn đã chạy 'uvicorn backend.api:app --reload'");
        console.error(error);
    } finally {
        btn.innerHTML = originalHTML;
        lucide.createIcons();
    }
});