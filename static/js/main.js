/* ── Фильтрация товаров по категориям ── */
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const cat = btn.dataset.category;
        document.querySelectorAll('.item-card').forEach(card => {
            const cardCat = card.dataset.categoryId || 'all';
            card.style.display = (cat === 'all' || cardCat === cat) ? '' : 'none';
        });
    });
});
