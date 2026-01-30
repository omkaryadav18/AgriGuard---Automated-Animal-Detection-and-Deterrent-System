document.addEventListener('DOMContentLoaded', function () {
    
    // --- 1. SLIDESHOW ---
    const slideshowContainers = document.querySelectorAll('.slideshow-container');
    slideshowContainers.forEach(container => {
        const slides = container.querySelectorAll('.slide');
        let currentSlide = 0;
        if (slides.length > 0) {
            function showSlide(index) {
                slides.forEach((slide, i) => {
                    slide.classList.remove('active');
                    if (i === index) slide.classList.add('active');
                });
            }
            function nextSlide() {
                currentSlide = (currentSlide + 1) % slides.length;
                showSlide(currentSlide);
            }
            showSlide(currentSlide);
            setInterval(nextSlide, 2000); 
        }
    });

    // --- 2. PASSWORD TOGGLE ---
    document.querySelectorAll('.password-toggle-icon').forEach(icon => {
        icon.addEventListener('click', function(e) {
            e.preventDefault();
            const group = this.closest('.form-group');
            const input = group.querySelector('input');
            if (input) {
                if (input.type === 'password') {
                    input.type = 'text';
                    this.textContent = '🙈';
                } else {
                    input.type = 'password';
                    this.textContent = '👁️';
                }
            }
        });
    });

    // --- 3. AUTH LOGIC ---
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const otpForm = document.getElementById('otp-form');
    const forgotForm = document.getElementById('forgot-form');
    let currentEmail = "";

    function switchForm(form) {
        [loginForm, registerForm, otpForm, forgotForm].forEach(f => { if(f) f.style.display = 'none'; });
        if(form) form.style.display = 'block';
    }

    if(document.getElementById('show-register')) document.getElementById('show-register').onclick = (e) => { e.preventDefault(); switchForm(registerForm); };
    if(document.getElementById('show-login')) document.getElementById('show-login').onclick = (e) => { e.preventDefault(); switchForm(loginForm); };
    if(document.getElementById('show-forgot')) document.getElementById('show-forgot').onclick = (e) => { e.preventDefault(); switchForm(forgotForm); };
    if(document.getElementById('cancel-otp')) document.getElementById('cancel-otp').onclick = (e) => { e.preventDefault(); switchForm(loginForm); };
    if(document.getElementById('cancel-forgot')) document.getElementById('cancel-forgot').onclick = (e) => { e.preventDefault(); switchForm(loginForm); };

    // Register Validation
    const regPass = document.getElementById('reg-password');
    const strengthBar = document.getElementById('strength-bar');
    const strengthMsg = document.getElementById('strength-msg');
    if(regPass) {
        regPass.addEventListener('input', function() {
            const val = this.value;
            let strength = 0;
            if(val.length >= 8) strength++;
            if(/[A-Za-z]/.test(val)) strength++;
            if(/[0-9]/.test(val)) strength++;
            if(/[^A-Za-z0-9]/.test(val)) strength++;
            if(val.length === 0) { strengthBar.style.width = '0%'; strengthMsg.textContent = ''; }
            else if(strength < 2 || val.length < 6) { strengthBar.style.width = '30%'; strengthBar.style.background = 'red'; strengthMsg.textContent = 'Weak'; strengthMsg.style.color = 'red'; }
            else if(strength < 4) { strengthBar.style.width = '60%'; strengthBar.style.background = 'orange'; strengthMsg.textContent = 'Medium'; strengthMsg.style.color = 'orange'; }
            else { strengthBar.style.width = '100%'; strengthBar.style.background = '#28a745'; strengthMsg.textContent = 'Strong!'; strengthMsg.style.color = '#28a745'; }
        });
    }

    // LOGIN
    if(loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const email = document.getElementById('login-email').value;
            const password = document.getElementById('login-password').value;
            currentEmail = email;
            fetch('/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) })
            .then(r => r.json()).then(data => {
                if (data.success && data.require_otp) { alert("✅ OTP Sent!"); switchForm(otpForm); }
                else { alert("❌ " + (data.message || "Login Failed")); }
            });
        });
    }

    // OTP
    if(otpForm) {
        otpForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const otp = document.getElementById('otp-input').value;
            fetch('/verify_login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: currentEmail, otp }) })
            .then(r => r.json()).then(data => { if (data.success) window.location.href = data.redirect_url; else alert("❌ " + data.message); });
        });
    }

    // FORGOT PASSWORD
    if(forgotForm) {
        forgotForm.addEventListener('submit', function(e) {
            e.preventDefault();
            if(document.getElementById('send-reset-btn').style.display !== 'none') {
                const email = document.getElementById('forgot-email').value;
                fetch('/request_reset', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email }) })
                .then(r => r.json()).then(data => {
                    if (data.success) {
                        alert("📧 OTP Sent!");
                        document.getElementById('reset-inputs').style.display = 'block';
                        document.getElementById('send-reset-btn').style.display = 'none';
                    } else { alert("✅ " + data.message); }
                });
            }
        });

        const confirmBtn = document.getElementById('confirm-reset-btn');
        if(confirmBtn) {
            confirmBtn.addEventListener('click', function() {
                const email = document.getElementById('forgot-email').value;
                const otp = document.getElementById('reset-otp').value;
                const newPass = document.getElementById('new-password').value;
                fetch('/reset_password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, otp, new_password: newPass }) })
                .then(r => r.json()).then(data => {
                    if (data.success) { alert("✅ Password Updated!"); switchForm(loginForm); }
                    else { alert("❌ " + data.message); }
                });
            });
        }
    }

    // REGISTER
    if(registerForm) {
        registerForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const fName = document.getElementById('reg-first-name').value;
            const lName = document.getElementById('reg-last-name').value;
            const email = document.getElementById('reg-email').value;
            const pass = document.getElementById('reg-password').value;
            const conf = document.getElementById('reg-confirm-password').value;
            if (pass !== conf) { alert("Passwords do not match"); return; }
            fetch('/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ first_name: fName, last_name: lName, email: email, password: pass }) })
            .then(r => r.json()).then(data => { if(data.success) { alert("✅ Success!"); switchForm(loginForm); } else { alert("❌ " + data.message); } });
        });
    }

    // --- 4. DATA PAGE LOGIC ---
    const tableBody = document.getElementById("data-table-body");
    if (tableBody) { 
        const searchBar = document.getElementById("search-bar");
        const selectBtn = document.getElementById("select-btn");
        const resetBtn = document.getElementById("reset-btn");
        const deleteBtn = document.getElementById("delete-btn");
        const selectAllCheckbox = document.getElementById("select-all-checkbox");
        let isSelectMode = false;

        function loadData() {
            if (typeof API_URL_GET === 'undefined') return;
            fetch(API_URL_GET + '?_=' + new Date().getTime()).then(r => r.json()).then(data => { renderTable(data); });
        }

        function renderTable(data) {
            tableBody.innerHTML = "";
            if (data.length === 0) { tableBody.innerHTML = '<tr><td colspan="5">No data found.</td></tr>'; return; }
            data.forEach(item => {
                let dateStr = item.timestamp.split(' ')[0]; let timeStr = item.timestamp.split(' ')[1];
                const row = document.createElement("tr");
                row.innerHTML = `<td class="select-col" style="display:${isSelectMode?'table-cell':'none'}"><input type="checkbox" class="row-checkbox" data-id="${item.id}" data-path="${item.image_path}"></td><td>${dateStr}</td><td>${timeStr}</td><td>${item.animal_name}</td><td><a href="${item.image_path}" target="_blank">View</a></td>`;
                tableBody.appendChild(row);
            });
        }

        searchBar.addEventListener("keyup", function(e) {
            const term = e.target.value.toLowerCase();
            const rows = tableBody.querySelectorAll("tr");
            rows.forEach(row => { row.style.display = row.innerText.toLowerCase().includes(term) ? "" : "none"; });
        });

        if(selectAllCheckbox) {
            selectAllCheckbox.addEventListener("change", function() {
                const isChecked = this.checked;
                tableBody.querySelectorAll("tr").forEach(row => { if(row.style.display !== "none") { const cb = row.querySelector(".row-checkbox"); if(cb) cb.checked = isChecked; } });
            });
        }

        selectBtn.addEventListener("click", () => { isSelectMode = true; toggleUI(); });
        resetBtn.addEventListener("click", () => { isSelectMode = false; toggleUI(); document.querySelectorAll(".row-checkbox").forEach(cb => cb.checked = false); });
        
        function toggleUI() {
            document.querySelectorAll(".select-col").forEach(col => col.style.display = isSelectMode ? "table-cell" : "none");
            selectBtn.style.display = isSelectMode ? "none" : "inline-block";
            resetBtn.style.display = isSelectMode ? "inline-block" : "none";
            deleteBtn.style.display = isSelectMode ? "inline-block" : "none";
        }

        deleteBtn.addEventListener("click", function() {
            const checkedBoxes = document.querySelectorAll(".row-checkbox:checked");
            if (checkedBoxes.length === 0) return alert("Select items.");
            if (!confirm(`Delete ${checkedBoxes.length} items?`)) return;
            const ids = Array.from(checkedBoxes).map(cb => cb.getAttribute("data-id"));
            const paths = Array.from(checkedBoxes).map(cb => cb.getAttribute("data-path"));
            fetch(API_URL_DELETE, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ids, image_paths: paths }) })
            .then(r => r.json()).then(res => { if (res.success) { loadData(); isSelectMode = false; toggleUI(); } });
        });

        loadData();
    }
});