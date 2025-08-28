window.addEventListener("DOMContentLoaded", function() {
    [].forEach.call(document.querySelectorAll('.tel'), function(input) {
        var keyCode;
        // Find the related hidden field (if exists)
        var hiddenField = document.getElementById(input.dataset.hiddenField || '');
        
        function mask(event) {
            event.keyCode && (keyCode = event.keyCode);
            var pos = this.selectionStart;
            if (pos < 3) event.preventDefault();
            var matrix = "+7 (___) ___ ____",
                i = 0,
                def = matrix.replace(/\D/g, ""),
                val = this.value.replace(/\D/g, ""),
                new_value = matrix.replace(/[_\d]/g, function(a) {
                    return i < val.length ? val.charAt(i++) || def.charAt(i) : a
                });
            i = new_value.indexOf("_");
            if (i != -1) {
                i < 5 && (i = 3);
                new_value = new_value.slice(0, i)
            }
            var reg = matrix.substr(0, this.value.length).replace(/_+/g,
                function(a) {
                    return "\\d{1," + a.length + "}"
                }).replace(/[+()]/g, "\\$&");
            reg = new RegExp("^" + reg + "$");
            if (!reg.test(this.value) || this.value.length < 5 || keyCode > 47 && keyCode < 58) this.value = new_value;
            
            // Update hidden field with the E.164 format
            if (hiddenField) {
                // Extract only the mobile number digits (after +7)
                // The mask format is "+7 (___) ___ ____" so we extract only the digits in the positions after +7
                var mobileDigits = this.value.replace(/^\+7\s*\(?/, '').replace(/\D/g, '');
                
                // Ensure we have exactly 10 digits for a valid mobile number
                if (mobileDigits.length > 0) {
                    // Limit to 10 digits max
                    mobileDigits = mobileDigits.substring(0, 10);
                    hiddenField.value = "+7" + mobileDigits;
                } else {
                    hiddenField.value = "";
                }
            }
            
            // Validate and set visual feedback
            validatePhone(this);
            
            if (event.type == "blur" && this.value.length < 5) this.value = "";
        }
        
        function validatePhone(input) {
            // Extract only the mobile number digits (after +7)
            var mobileDigits = input.value.replace(/^\+7\s*\(?/, '').replace(/\D/g, '');
            
            // If there are no digits at all, don't validate
            if (mobileDigits.length === 0) {
                input.classList.remove('is-valid', 'is-invalid');
                return false;
            }
            
            // A valid mobile number should have exactly 10 digits
            var isValid = mobileDigits.length === 10;
            
            // Apply validation classes
            input.classList.toggle('is-valid', isValid);
            input.classList.toggle('is-invalid', !isValid);
            
            return isValid;
        }
        
        // Initialize from hidden field if it has a value
        if (hiddenField && hiddenField.value) {
            var initialValue = hiddenField.value;
            var digits = initialValue.replace(/\D/g, "");
            // If starts with 7, remove it (since mask adds +7)
            if (digits.length === 11 && digits.charAt(0) === '7') {
                digits = digits.substring(1);
            }
            
            // Format the visible field according to the mask
            if (digits.length > 0 && digits.length <= 10) {
                input.value = "+7";
                if (digits.length > 0) input.value += " (" + digits.substring(0, 3);
                if (digits.length > 3) input.value += ") " + digits.substring(3, 6);
                if (digits.length > 6) input.value += " " + digits.substring(6, 8);
                if (digits.length > 8) input.value += " " + digits.substring(8, 10);
                
                validatePhone(input);
            }
        }

        input.addEventListener("input", mask, false);
        input.addEventListener("focus", mask, false);
        input.addEventListener("blur", mask, false);
        input.addEventListener("keydown", mask, false);
        
        // Form validation on submit
        var form = input.closest('form');
        if (form) {
            form.addEventListener('submit', function(e) {
                // First ensure the input field is fully masked
                mask.call(input, {type: 'input'});
                
                // Then validate
                var isValid = validatePhone(input);
                
                // Only prevent submission if there's content and it's invalid
                if (input.value && !isValid) {
                    e.preventDefault();
                    input.focus();
                    // Add an error message
                    var errorMsg = document.createElement('div');
                    errorMsg.className = 'invalid-feedback d-block';
                    errorMsg.textContent = 'Пожалуйста, введите корректный 10-значный номер телефона';
                    
                    // Check if there's already an error message
                    var existingError = input.parentNode.querySelector('.invalid-feedback');
                    if (!existingError) {
                        input.parentNode.appendChild(errorMsg);
                    }
                }
            });
        }
    });
});
