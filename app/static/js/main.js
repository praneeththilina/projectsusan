// // app/static/js/main.js
// Adding transition effect to links when clicked
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', (event) => {
      event.preventDefault();
      const targetUrl = event.target.href;
      document.documentElement.classList.add('transition-light-dark');
      setTimeout(() => {
          window.location.href = targetUrl;
      }, 300);  // Adjust the delay as needed
  });
});

document.addEventListener("DOMContentLoaded", function() {
  const toasts = document.querySelectorAll(".toast");
  toasts.forEach(toast => {
    setTimeout(() => {
      toast.style.display = "none";
    }, 5000); // 5 seconds
  });
});

// input mask percent 
document.addEventListener('DOMContentLoaded', function() {
  const percentageInputs = document.querySelectorAll('.percentage-input');
  percentageInputs.forEach(input => {
      input.addEventListener('input', function() {
          let value = this.value.replace(/[^\d.]/g, ''); // Remove any non-numeric characters
          if (value) {
              value = parseFloat(value);
              if (value > 100) value = 100; // Ensure the value doesn't exceed 100
              this.value = value;
          }
      });
  });
});