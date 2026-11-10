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

  // Pencarian dan filter tabel inventaris (berjalan pada data yang sedang tampil).
  const searchFields = document.querySelectorAll("#inventory-search, .table-search");
  searchFields.forEach(function (field) {
    field.addEventListener("input", function () {
      const table = field.closest(".content-card").querySelector("tbody");
      const query = field.value.toLocaleLowerCase("id");
      table.querySelectorAll("tr").forEach(function (row) {
        row.hidden = !row.textContent.toLocaleLowerCase("id").includes(query);
      });
    });
  });

  const statusFilter = document.getElementById("status-filter");
  if (statusFilter) {
    statusFilter.addEventListener("change", function () {
      document.querySelectorAll("#inventory-table tbody tr").forEach(function (row) {
        row.hidden = (statusFilter.value && !row.cells[5]?.textContent.includes(statusFilter.value)) ||
          !row.textContent.toLocaleLowerCase("id").includes(document.getElementById("inventory-search").value.toLocaleLowerCase("id"));
      });
    });
    document.getElementById("inventory-search").addEventListener("input", function () {
      statusFilter.dispatchEvent(new Event("change"));
    });
  }

});
