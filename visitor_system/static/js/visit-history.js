// Alpine component for Visit History table client interactions (selection, filter toggle)
window.VisitHistory = function () {
  return {
    filterSelected: false,
    toggleFilterSelected() {
      this.filterSelected = !this.filterSelected;
      const rows = document.querySelectorAll('.table-tbody tr');
      rows.forEach((row) => {
        const chk = row.querySelector('input.table-selectable-check');
        row.style.display = this.filterSelected ? (chk && chk.checked ? '' : 'none') : '';
      });
    },
  };
};

// Re-apply row filtering after HTMX update
document.addEventListener('htmx:afterSwap', function (evt) {
  try {
    const root = document.querySelector('[x-data^="VisitHistory"]');
    if (root && root.__x) {
      // trigger refresh of filter state
      const api = root.__x.$data;
      if (api.filterSelected) {
        api.toggleFilterSelected();
        api.toggleFilterSelected();
      }
    }
  } catch (e) {}
});
