document.addEventListener("DOMContentLoaded", function () {
  const passwordInput = document.getElementById("password");
  const togglePassword = document.getElementById("toggle-password");

  const roleInput = document.getElementById("selected-role");
  const roleButtons = document.querySelectorAll(".access-button");

  // Menampilkan atau menyembunyikan password
  if (passwordInput && togglePassword) {
    togglePassword.addEventListener("click", function () {
      if (passwordInput.type === "password") {
        passwordInput.type = "text";
      } else {
        passwordInput.type = "password";
      }
    });
  }

  // Memilih akses Admin atau Pembimbing
  roleButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      roleButtons.forEach(function (item) {
        item.classList.remove("active");
      });

      button.classList.add("active");

      if (roleInput) {
        roleInput.value = button.dataset.role;
      }
    });
  });
});
