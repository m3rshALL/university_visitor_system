// Функция для сортировки таблицы
document.addEventListener('DOMContentLoaded', function() {
    // Функция для получения значения ячейки
    const getCellValue = (tr, idx) => {
        // Учитываем, что первая колонка - это пустая ячейка с чекбоксом
        const cell = tr.children[idx];
        if (!cell) return '';
        
        // Особая обработка для дат
        if (idx === 4 || idx === 5) { // Столбцы с датами входа и выхода
            // Сначала проверим, содержит ли ячейка конкретную дату
            const dateText = cell.textContent.trim();
            const dateMatch = dateText.match(/\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}/);
            if (dateMatch) {
                return dateMatch[0];
            }
            
            // Если нет даты, проверяем на статусы
            if (dateText.includes('Ожидается')) return 'awaiting';
            if (dateText.includes('В здании')) return 'in_building';
            if (dateText.includes('Покинул')) return 'left';
            if (dateText.includes('Отменен')) return 'cancelled';
            
            return dateText;
        }
        
        // Для обычных ячеек возвращаем текст
        return cell.textContent.trim();
    };

    // Функция сравнения для сортировки
    const comparer = (idx, asc) => (a, b) => {
        // Получаем значения для сравнения
        const v1 = getCellValue(asc ? a : b, idx);
        const v2 = getCellValue(asc ? b : a, idx);
        
        // Проверяем, содержит ли ячейка дату и время
        const datePattern = /^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}$/;
        
        if (datePattern.test(v1) && datePattern.test(v2)) {
            // Сортировка по дате
            return new Date(v1) - new Date(v2);
        } else if (idx === 4 || idx === 5) {
            // Сортировка по статусам для столбцов времени входа/выхода
            const statusOrder = {
                'in_building': 1,
                'awaiting': 2,
                'left': 3,
                'cancelled': 4,
                '': 5
            };
            
            const order1 = statusOrder[v1] || 5;
            const order2 = statusOrder[v2] || 5;
            return order1 - order2;
        } else {
            // Обычная сортировка по тексту или числам
            if (v1 !== '' && v2 !== '' && !isNaN(v1) && !isNaN(v2)) {
                return parseFloat(v1) - parseFloat(v2);
            } else {
                return v1.toString().localeCompare(v2.toString());
            }
        }
    };

    // Добавляем обработчики к заголовкам таблицы
    document.querySelectorAll('.table-sort').forEach(th => {
        th.addEventListener('click', function() {
            const table = th.closest('table');
            const tbody = table.querySelector('tbody');
            // Находим индекс столбца для сортировки (учитывая возможные nested элементы)
            const thParent = th.closest('th');
            const thIndex = Array.from(thParent.parentNode.children).indexOf(thParent);
            
            // Если уже есть стрелка, меняем направление сортировки
            let sortDirection = this.classList.contains('sorted-asc') ? false : true;
            
            // Удаляем классы сортировки у всех заголовков и кнопок
            table.querySelectorAll('th button.table-sort').forEach(el => {
                el.classList.remove('sorted-asc', 'sorted-desc');
            });
            
            // Добавляем класс сортировки текущему заголовку
            this.classList.add(sortDirection ? 'sorted-asc' : 'sorted-desc');
            
            // Сортируем строки
            Array.from(tbody.querySelectorAll('tr'))
                .sort(comparer(thIndex, sortDirection))
                .forEach(tr => tbody.appendChild(tr));
        });
    });
});
