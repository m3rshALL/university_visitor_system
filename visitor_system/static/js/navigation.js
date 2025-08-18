// Универсальная навигация "Назад" с безопасным фолбэком
document.addEventListener('DOMContentLoaded', function() {
	window.goBackOr = function(defaultUrl) {
		try {
			const hasHistory = window.history.length > 1;
			const ref = document.referrer;
			let sameOrigin = false;
			if (ref) {
				const refUrl = new URL(ref, window.location.href);
				sameOrigin = refUrl.origin === window.location.origin;
			}
			if (hasHistory && sameOrigin) {
				window.history.back();
			} else {
				window.location.href = defaultUrl;
			}
		} catch (e) {
			window.location.href = defaultUrl;
		}
	};

	// Делегирование по атрибуту data-go-back
	document.querySelectorAll('[data-go-back]')
		.forEach(function(el) {
			el.addEventListener('click', function(ev) {
				ev.preventDefault();
				const url = el.getAttribute('data-back-url') || '/';
				window.goBackOr(url);
			});
		});
});


