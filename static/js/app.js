(function () {
  const scrollKey = `selectora:scroll:${window.location.pathname}`;

  function shouldPreserveScroll(element) {
    if (!element || element.target === "_blank") {
      return false;
    }
    return Boolean(
      element.closest(".tag-cloud") ||
      element.closest(".active-tags") ||
      element.closest(".tag-tools") ||
      element.closest(".compact-tag-drawer")
    );
  }

  function saveScrollPosition() {
    sessionStorage.setItem(scrollKey, String(window.scrollY));
  }

  document.addEventListener("click", function (event) {
    const link = event.target.closest("a");
    if (shouldPreserveScroll(link)) {
      saveScrollPosition();
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    const savedPosition = sessionStorage.getItem(scrollKey);
    if (!savedPosition) {
      return;
    }
    sessionStorage.removeItem(scrollKey);
    window.requestAnimationFrame(function () {
      window.scrollTo({ top: Number(savedPosition), left: 0, behavior: "instant" });
    });
  });
})();
