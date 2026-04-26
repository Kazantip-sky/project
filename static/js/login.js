/* ═══════════════════════════════════════════════════════════════
   LOGIN PAGE  —  static/js/login.js
   Подключается только на странице /login
   ═══════════════════════════════════════════════════════════════ */

/**
 * Переключение вкладок Ученик / Учитель.
 * @param {string} tab   — 'student' | 'teacher'
 * @param {HTMLElement} clickedBtn — нажатая кнопка
 */
function loginSwitchTab(tab, clickedBtn) {
    // Снять active со всех кнопок и панелей
    document.querySelectorAll('.login-tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.login-panel').forEach(p => p.classList.remove('active'));

    // Активировать нужную кнопку и панель
    if (clickedBtn) clickedBtn.classList.add('active');
    const panel = document.getElementById('login-panel-' + tab);
    if (panel) panel.classList.add('active');

    // При смене на вкладку "Ученик" — закрыть форму admin
    if (tab === 'student') {
        const adminForm = document.getElementById('login-admin-form');
        const adminText = document.getElementById('login-admin-toggle-text');
        if (adminForm) adminForm.classList.remove('open');
        if (adminText) adminText.textContent = 'Войти от имени администратора';
    }
}

/**
 * Раскрыть / скрыть вложенную форму администратора.
 */
function loginToggleAdmin() {
    const form = document.getElementById('login-admin-form');
    const text = document.getElementById('login-admin-toggle-text');
    if (!form) return;

    const isOpen = form.classList.toggle('open');
    if (text) {
        text.textContent = isOpen
            ? 'Скрыть форму администратора'
            : 'Войти от имени администратора';
    }
}
