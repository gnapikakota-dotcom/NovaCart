const mobileToggle = document.getElementById("mobileToggle");
const mainNav = document.getElementById("mainNav");
if (mobileToggle && mainNav) {
  mobileToggle.addEventListener("click", () => mainNav.classList.toggle("open"));
}
document.querySelectorAll("form[data-confirm]").forEach(form => {
  form.addEventListener("submit", event => {
    if (!confirm(form.dataset.confirm)) event.preventDefault();
  });
});
document.querySelectorAll(".flash").forEach(flash => {
  window.setTimeout(() => flash.classList.add("flash-hide"), 5000);
});
