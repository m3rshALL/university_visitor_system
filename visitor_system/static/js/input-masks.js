// Маска телефона: +7 771 111 11 11 (пробелы)
document.addEventListener('DOMContentLoaded', function () {
  const applyPhoneMask = (input) => {
    function formatToMask(value) {
      let digits = value.replace(/\D/g, '');
      if (digits.startsWith('8')) digits = '7' + digits.slice(1);
      if (digits.startsWith('7')) digits = digits.slice(1);
      const d = digits.substring(0, 10);
      let res = '+7';
      if (!d.length) return res;
      res += ' ' + d.substring(0, 3);
      if (d.length >= 3) res += ' ' + d.substring(3, 6);
      if (d.length >= 6) res += ' ' + d.substring(6, 8);
      if (d.length >= 8) res += ' ' + d.substring(8, 10);
      return res;
    }
    function toE164(value) {
      let digits = value.replace(/\D/g, '');
      if (digits.length === 11 && digits.startsWith('8')) digits = '7' + digits.slice(1);
      if (digits.length === 10) digits = '7' + digits;
      if (!digits.startsWith('7')) return value;
      return '+' + digits.substring(0, 11);
    }
    input.addEventListener('input', () => {
      input.value = formatToMask(input.value);
      input.setSelectionRange(input.value.length, input.value.length);
    });
    input.addEventListener('blur', () => {
      input.value = toE164(input.value);
    });
    // Инициализация отображения
    if (input.value) input.value = formatToMask(input.value);
  };

  document.querySelectorAll('input[data-mask="phone"]').forEach(applyPhoneMask);
});


