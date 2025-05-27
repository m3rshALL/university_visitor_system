// Модуль для обработки кнопки "Выход" посетителя
document.addEventListener('DOMContentLoaded', function() {
    const exitButtons = document.querySelectorAll('.exit-button, button[data-action="exit"], form[action*="record_exit"] button[type="submit"]');
    
    // Если на странице есть кнопки выхода
    if (exitButtons && exitButtons.length > 0) {
        exitButtons.forEach(button => {
            button.addEventListener('click', handleExitClick);
        });
    }
    
    // Обработчик клика по кнопке выхода
    function handleExitClick(event) {
        // Добавляем индикатор загрузки
        const originalContent = this.innerHTML;
        this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Обработка...';
        this.disabled = true;
        
        // Продолжаем стандартную отправку формы
        const form = this.closest('form');
        if (form) {
            // Форма продолжит отправку нормально
            // setTimeout чтобы успел отобразиться спиннер
            setTimeout(() => {}, 10);
        } else {
            // Если это просто кнопка, а не форма
            console.log("Кнопка выхода не привязана к форме");
        }
    }
});
