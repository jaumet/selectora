(function () {
  let deferredInstallPrompt = null;

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function () {});
    });
  }

  function isStandalonePwa() {
    return window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
  }

  function isIos() {
    return /iphone|ipad|ipod/i.test(window.navigator.userAgent);
  }

  function setupInstallButton() {
    const button = document.querySelector("[data-pwa-install]");
    if (!button || isStandalonePwa()) {
      return;
    }
    if (deferredInstallPrompt || isIos()) {
      button.hidden = false;
    }
    button.addEventListener("click", async function () {
      if (deferredInstallPrompt) {
        deferredInstallPrompt.prompt();
        await deferredInstallPrompt.userChoice.catch(function () {});
        deferredInstallPrompt = null;
        button.hidden = true;
        return;
      }
      window.alert("Per instal·lar Selectora a iPhone o iPad: obre el botó de compartir del navegador i tria 'Afegir a pantalla d’inici'.");
    });
  }

  window.addEventListener("beforeinstallprompt", function (event) {
    event.preventDefault();
    deferredInstallPrompt = event;
    const button = document.querySelector("[data-pwa-install]");
    if (button && !isStandalonePwa()) {
      button.hidden = false;
    }
  });

  window.addEventListener("appinstalled", function () {
    deferredInstallPrompt = null;
    const button = document.querySelector("[data-pwa-install]");
    if (button) {
      button.hidden = true;
    }
  });

  document.addEventListener("DOMContentLoaded", setupInstallButton);
})();

(function () {
  function openDrawer(id) {
    const drawer = document.getElementById(id);
    if (!drawer) {
      return false;
    }
    if (drawer.tagName === "DETAILS") {
      drawer.open = true;
    } else if (drawer.classList.contains("compact-panel")) {
      document.querySelectorAll(".compact-panel.is-open").forEach(function (panel) {
        if (panel !== drawer) {
          panel.classList.remove("is-open");
        }
      });
      drawer.classList.add("is-open");
    } else {
      return false;
    }
    drawer.scrollIntoView({ block: "start", behavior: "smooth" });
    syncDrawerTriggers(id);
    return true;
  }

  function syncDrawerTriggers(activeId) {
    document.querySelectorAll("[data-open-drawer]").forEach(function (trigger) {
      const isActive = trigger.dataset.openDrawer === activeId;
      trigger.classList.toggle("is-active", isActive);
      trigger.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
  }

  function closeDrawer(id) {
    const drawer = document.getElementById(id);
    if (!drawer) {
      return false;
    }
    if (drawer.tagName === "DETAILS") {
      drawer.open = false;
    } else if (drawer.classList.contains("compact-panel")) {
      drawer.classList.remove("is-open");
    } else {
      return false;
    }
    syncDrawerTriggers("");
    if (window.location.hash === `#${id}`) {
      history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
    }
    return true;
  }

  function toggleDrawer(id) {
    const drawer = document.getElementById(id);
    if (!drawer) {
      return false;
    }
    const isOpen = drawer.tagName === "DETAILS" ? drawer.open : drawer.classList.contains("is-open");
    if (isOpen) {
      return closeDrawer(id);
    }
    return openDrawer(id);
  }

  function updateRailControls(shell) {
    const rail = shell.querySelector("[data-media-rail]");
    const prev = shell.querySelector("[data-rail-prev]");
    const next = shell.querySelector("[data-rail-next]");
    if (!rail || !prev || !next) {
      return;
    }
    const maxScroll = rail.scrollWidth - rail.clientWidth;
    const hasOverflow = maxScroll > 2;
    prev.hidden = !hasOverflow;
    next.hidden = !hasOverflow;
    prev.disabled = rail.scrollLeft <= 2;
    next.disabled = rail.scrollLeft >= maxScroll - 2;
  }

  function scrollRail(button, direction) {
    const shell = button.closest(".media-rail-shell");
    const rail = shell ? shell.querySelector("[data-media-rail]") : null;
    if (!rail) {
      return;
    }
    const firstItem = rail.querySelector(".visual-card");
    const secondItem = firstItem ? firstItem.nextElementSibling : null;
    const itemStep = secondItem
      ? secondItem.offsetLeft - firstItem.offsetLeft
      : firstItem
        ? firstItem.offsetWidth
        : Math.max(rail.clientWidth, 320);
    const visibleItems = Math.max(1, Math.floor((rail.clientWidth + 1) / itemStep));
    const scrollItems = Math.max(1, visibleItems - 1);

    rail.scrollBy({
      left: direction * itemStep * scrollItems,
      behavior: "smooth",
    });
  }

  function initHomeIntro() {
    const overlay = document.querySelector("[data-home-intro]");
    if (!overlay) {
      return;
    }
    const storageKey = "selectora:home-intro-dismissed";
    try {
      if (localStorage.getItem(storageKey) === "1") {
        return;
      }
    } catch (error) {
      // localStorage can be unavailable in some privacy modes.
    }

    const remember = overlay.querySelector("[data-home-intro-never]");

    function closeIntro() {
      if (remember && remember.checked) {
        try {
          localStorage.setItem(storageKey, "1");
        } catch (error) {}
      }
      overlay.hidden = true;
      document.removeEventListener("keydown", closeOnEscape);
    }

    function closeOnEscape(event) {
      if (event.key === "Escape") {
        closeIntro();
      }
    }

    overlay.hidden = false;
    document.addEventListener("keydown", closeOnEscape);
    overlay.querySelectorAll("[data-home-intro-close]").forEach(function (button) {
      button.addEventListener("click", closeIntro);
    });
  }

  function initDeletePanel() {
    const panel = document.querySelector("[data-delete-panel]");
    const openButton = document.querySelector("[data-delete-panel-open]");
    if (!panel || !openButton) {
      return;
    }
    const closeButton = panel.querySelector("[data-delete-panel-close]");
    const confirm = panel.querySelector("[data-delete-confirm]");
    const submit = panel.querySelector("[data-delete-submit]");

    openButton.addEventListener("click", function () {
      panel.hidden = false;
      panel.scrollIntoView({ block: "center", behavior: "smooth" });
      if (confirm) {
        confirm.focus();
      }
    });

    if (closeButton) {
      closeButton.addEventListener("click", function () {
        panel.hidden = true;
        if (confirm) {
          confirm.checked = false;
        }
        if (submit) {
          submit.disabled = true;
        }
        openButton.focus();
      });
    }

    if (confirm && submit) {
      confirm.addEventListener("change", function () {
        submit.disabled = !confirm.checked;
      });
    }
  }

  function initVisibilityControls() {
    document.querySelectorAll("[data-visibility-control]").forEach(function (control) {
      const select = control.querySelector("select");
      const state = control.querySelector("[data-visibility-state]");
      const help = control.querySelector("[data-visibility-help]");
      if (!select) {
        return;
      }

      function syncVisibility() {
        const isPrivate = select.value === "private";
        control.classList.toggle("is-private", isPrivate);
        control.classList.toggle("is-public", !isPrivate);
        if (state) {
          state.textContent = isPrivate ? "Privat" : "Públic";
        }
        if (help) {
          help.textContent = isPrivate
            ? "Aquest ítem no es mostrarà a cap altre usuari; només el veus tu, creador del canal."
            : "Aquest ítem es mostrarà als altres usuaris dins del teu canal públic.";
        }
      }

      syncVisibility();
      select.addEventListener("change", syncVisibility);
    });
  }

  function initRatingForms() {
    document.querySelectorAll("[data-rating-form]").forEach(function (form) {
      const mainInput = form.querySelector("[data-rating-main-input]");
      const submit = form.querySelector("[data-rating-submit]");
      const limit = form.querySelector("[data-rating-limit]");
      const mainButtons = Array.from(form.querySelectorAll("[data-rating-main]"));
      const nuanceButtons = Array.from(form.querySelectorAll("[data-rating-nuance]"));

      function selectedNuanceInputs() {
        return Array.from(form.querySelectorAll("[data-rating-nuance-input]:checked"));
      }

      function syncSubmit() {
        if (submit && mainInput) {
          submit.disabled = !mainInput.value;
        }
        if (limit) {
          const count = selectedNuanceInputs().length;
          limit.textContent = count ? count + "/3 matisos seleccionats." : "Tria fins a 3 matisos.";
        }
      }

      mainButtons.forEach(function (button) {
        button.addEventListener("click", function () {
          if (!mainInput) {
            return;
          }
          const wasSelected = button.classList.contains("is-selected");
          mainInput.value = wasSelected ? "" : button.dataset.ratingMain;
          mainButtons.forEach(function (otherButton) {
            const selected = !wasSelected && otherButton === button;
            otherButton.classList.toggle("is-selected", selected);
            otherButton.setAttribute("aria-pressed", selected ? "true" : "false");
          });
          syncSubmit();
        });
      });

      nuanceButtons.forEach(function (button) {
        button.addEventListener("click", function () {
          const input = form.querySelector('[data-rating-nuance-input="' + button.dataset.ratingNuance + '"]');
          if (!input) {
            return;
          }
          if (!input.checked && selectedNuanceInputs().length >= 3) {
            if (limit) {
              limit.textContent = "Màxim 3 matisos.";
            }
            return;
          }
          input.checked = !input.checked;
          button.classList.toggle("is-selected", input.checked);
          button.setAttribute("aria-pressed", input.checked ? "true" : "false");
          syncSubmit();
        });
      });

      syncSubmit();
    });
  }

  function initHomeSectionSorting() {
    const container = document.querySelector("[data-home-sections]");
    if (!container) {
      return;
    }
    const storageKey = "selectora:home-section-order";
    let draggedSection = null;

    function sortableSections() {
      return Array.from(container.querySelectorAll("[data-home-sortable-section]"));
    }

    function saveSectionOrder() {
      const order = sortableSections()
        .map(function (section) {
          return section.dataset.homeSectionKey;
        })
        .filter(Boolean);
      try {
        localStorage.setItem(storageKey, JSON.stringify(order));
      } catch (error) {}
    }

    function applySavedOrder() {
      let order = [];
      try {
        order = JSON.parse(localStorage.getItem(storageKey) || "[]");
      } catch (error) {
        order = [];
      }
      if (!Array.isArray(order) || !order.length) {
        return;
      }
      const sectionsByKey = new Map(
        sortableSections().map(function (section) {
          return [section.dataset.homeSectionKey, section];
        })
      );
      order.forEach(function (key) {
        const section = sectionsByKey.get(key);
        if (section) {
          container.appendChild(section);
        }
      });
    }

    function sectionAfterPointer(y) {
      return sortableSections()
        .filter(function (section) {
          return section !== draggedSection;
        })
        .reduce(
          function (closest, section) {
            const box = section.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            if (offset < 0 && offset > closest.offset) {
              return { offset, section };
            }
            return closest;
          },
          { offset: Number.NEGATIVE_INFINITY, section: null }
        ).section;
    }

    applySavedOrder();

    container.querySelectorAll("[data-section-drag-handle]").forEach(function (handle) {
      handle.addEventListener("dragstart", function (event) {
        draggedSection = handle.closest("[data-home-sortable-section]");
        if (!draggedSection) {
          return;
        }
        draggedSection.classList.add("is-dragging");
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", draggedSection.dataset.homeSectionKey || "");
      });

      handle.addEventListener("dragend", function () {
        if (draggedSection) {
          draggedSection.classList.remove("is-dragging");
          draggedSection = null;
          saveSectionOrder();
          document.querySelectorAll(".media-rail-shell").forEach(updateRailControls);
        }
      });
    });

    container.addEventListener("dragover", function (event) {
      if (!draggedSection) {
        return;
      }
      event.preventDefault();
      const nextSection = sectionAfterPointer(event.clientY);
      if (nextSection) {
        container.insertBefore(draggedSection, nextSection);
      } else {
        container.appendChild(draggedSection);
      }
    });
  }

  document.addEventListener("click", function (event) {
    const prevRail = event.target.closest("[data-rail-prev]");
    if (prevRail) {
      scrollRail(prevRail, -1);
      return;
    }

    const nextRail = event.target.closest("[data-rail-next]");
    if (nextRail) {
      scrollRail(nextRail, 1);
      return;
    }

    const trigger = event.target.closest("[data-open-drawer]");
    if (!trigger) {
      return;
    }
    const targetId = trigger.dataset.openDrawer;
    const samePage = new URL(trigger.href, window.location.href).pathname === window.location.pathname;
    if (!samePage) {
      return;
    }
    if (toggleDrawer(targetId)) {
      event.preventDefault();
    }
  });

  function cookieValue(name) {
    const cookies = document.cookie ? document.cookie.split(";") : [];
    for (const cookie of cookies) {
      const trimmed = cookie.trim();
      if (trimmed.startsWith(`${name}=`)) {
        return decodeURIComponent(trimmed.slice(name.length + 1));
      }
    }
    return "";
  }

  function isPendingSection(card) {
    const section = card ? card.closest("section") : null;
    const heading = section ? section.querySelector(".section-heading h2") : null;
    return heading && heading.textContent.trim() === "Items pendents de veure";
  }

  function removePendingCard(card) {
    if (!card || !isPendingSection(card)) {
      return;
    }
    const section = card.closest("section");
    const count = section ? section.querySelector(".section-heading p") : null;
    card.remove();
    if (count) {
      const remaining = section.querySelectorAll(".visual-card").length;
      count.textContent = `${remaining} items`;
      if (!remaining) {
        section.remove();
      }
    }
  }

  function syncVisitToggle(visited) {
    const form = document.querySelector("[data-visit-toggle-form]");
    if (!form) {
      return;
    }
    const input = form.querySelector("[data-visit-toggle-input]");
    const button = form.querySelector("[data-visit-toggle-button]");
    if (input) {
      input.value = visited ? "0" : "1";
    }
    if (button) {
      button.textContent = visited ? "Marcar com a pendent" : "Marcar com a visitat";
    }
  }

  function markCardVisited(card) {
    if (!card) {
      return;
    }
    card.classList.add("is-visited");
    const image = card.querySelector(".card-image");
    if (image && !image.querySelector(".visited-badge")) {
      const badge = document.createElement("span");
      badge.className = "visited-badge";
      badge.setAttribute("aria-label", "Item visitat");
      badge.setAttribute("title", "Item visitat");
      image.appendChild(badge);
    }
  }

  async function markVisited(url, card) {
    if (!url) {
      return;
    }
    const csrfToken = cookieValue("csrftoken");
    if (!csrfToken) {
      return;
    }
    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      keepalive: true,
      headers: {
        "X-CSRFToken": csrfToken,
        "X-Requested-With": "XMLHttpRequest",
      },
    });
    if (response.ok) {
      markCardVisited(card);
      removePendingCard(card);
      syncVisitToggle(true);
    }
  }

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
    const visitedLink = event.target.closest("[data-mark-visited-url]");
    if (visitedLink) {
      markVisited(visitedLink.dataset.markVisitedUrl, visitedLink.closest(".visual-card")).catch(function () {});
    }

    const link = event.target.closest("a");
    if (shouldPreserveScroll(link)) {
      saveScrollPosition();
    }
  });

  document.addEventListener(
    "pointerdown",
    function (event) {
      const localPlayer = event.target.closest("[data-mark-visited-on-interaction]");
      if (localPlayer) {
        localPlayer.dataset.visitInteractionStarted = "1";
        markVisited(localPlayer.dataset.markVisitedUrl, localPlayer.closest(".visual-card")).catch(function () {});
      }
    },
    true
  );

  window.addEventListener("blur", function () {
    const activeElement = document.activeElement;
    if (!activeElement || !activeElement.matches("[data-mark-visited-on-interaction]")) {
      return;
    }
    if (activeElement.dataset.visitInteractionStarted === "1") {
      return;
    }
    activeElement.dataset.visitInteractionStarted = "1";
    markVisited(activeElement.dataset.markVisitedUrl, activeElement.closest(".visual-card")).catch(function () {});
  });

  document.addEventListener(
    "focusin",
    function (event) {
      const localPlayer = event.target.closest("[data-mark-visited-on-interaction]");
      if (!localPlayer || localPlayer.dataset.visitInteractionStarted === "1") {
        return;
      }
      localPlayer.dataset.visitInteractionStarted = "1";
      markVisited(localPlayer.dataset.markVisitedUrl, localPlayer.closest(".visual-card")).catch(function () {});
    },
    true
  );

  document.addEventListener("DOMContentLoaded", function () {
    initHomeIntro();
    initDeletePanel();
    initVisibilityControls();
    initRatingForms();
    initHomeSectionSorting();

    document.querySelectorAll(".media-rail-shell").forEach(function (shell) {
      const rail = shell.querySelector("[data-media-rail]");
      updateRailControls(shell);
      if (rail) {
        rail.addEventListener("scroll", function () {
          updateRailControls(shell);
        });
      }
    });

    window.addEventListener("resize", function () {
      document.querySelectorAll(".media-rail-shell").forEach(updateRailControls);
    });

    document.querySelectorAll("[data-image-fallback]").forEach(function (image) {
      function showFallback() {
        const cardImage = image.closest(".card-image");
        if (cardImage) {
          cardImage.classList.add("image-missing");
        }
      }

      image.addEventListener("error", showFallback, { once: true });
      if (image.complete && image.naturalWidth === 0) {
        showFallback();
      }
    });

    const savedPosition = sessionStorage.getItem(scrollKey);
    if (!savedPosition) {
      const hash = window.location.hash.replace("#", "");
      if (hash === "temes" || hash === "cerca") {
        window.requestAnimationFrame(function () {
          openDrawer(hash);
        });
      }
      return;
    }
    sessionStorage.removeItem(scrollKey);
    window.requestAnimationFrame(function () {
      window.scrollTo({ top: Number(savedPosition), left: 0, behavior: "instant" });
    });
    const hash = window.location.hash.replace("#", "");
    if (hash === "temes" || hash === "cerca") {
      window.requestAnimationFrame(function () {
        openDrawer(hash);
      });
    }
  });
})();

(function () {
  function absoluteUrl(url) {
    return new URL(url, window.location.origin).href;
  }

  function buildPublicItemUrl(item) {
    return absoluteUrl(item.url);
  }

  function buildPublicCollectionUrl(collection) {
    return absoluteUrl(collection.url);
  }

  function buildPublicChannelUrl(user) {
    return absoluteUrl(user.url);
  }

  function buildSiteShareText(site, url) {
    return [site.title, "", site.description, "", url].filter(Boolean).join("\n");
  }

  async function copyToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return;
    }
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.top = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  }

  function buildItemShareText(item, url) {
    return ["I found this on Selectora:", "", item.title, item.description ? `\n${item.description}` : "", "", url]
      .filter((part, index) => part || index === 1 || index === 4)
      .join("\n");
  }

  function buildCollectionShareText(collection, url) {
    return [
      "A human-curated collection on Selectora:",
      "",
      collection.title,
      collection.description ? `\n${collection.description}` : "",
      "",
      url,
    ]
      .filter((part, index) => part || index === 1 || index === 4)
      .join("\n");
  }

  function buildChannelShareText(user, url) {
    return `${user.title}'s Selectora channel:\n\n${url}`;
  }

  function payloadFromElement(element) {
    const type = element.dataset.shareType || "item";
    const data = {
      title: element.dataset.shareTitle || document.title,
      description: element.dataset.shareDescription || "",
      curator: element.dataset.shareCurator || "",
      url: element.dataset.shareUrl || window.location.pathname,
    };
    const builders = {
      item: { url: buildPublicItemUrl, text: buildItemShareText },
      collection: { url: buildPublicCollectionUrl, text: buildCollectionShareText },
      channel: { url: buildPublicChannelUrl, text: buildChannelShareText },
      site: { url: buildPublicChannelUrl, text: buildSiteShareText },
    };
    const builder = builders[type] || builders.item;
    const url = builder.url(data);
    return {
      title: data.title,
      text: builder.text(data, url),
      url,
    };
  }

  function statusFor(element) {
    const menu = element.closest("[data-share-menu]");
    return menu ? menu.querySelector("[data-share-status]") : null;
  }

  function showCopied(element, message) {
    const status = statusFor(element);
    if (!status) {
      return;
    }
    status.textContent = message;
    window.setTimeout(function () {
      status.textContent = "";
    }, 1600);
  }

  async function shareViaNativeOrFallback(payload) {
    if (navigator.share) {
      await navigator.share(payload);
      return true;
    }
    await copyToClipboard(payload.url);
    return false;
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-share-native]").forEach(function (button) {
      if (!navigator.share) {
        button.hidden = true;
      }
    });

    document.querySelectorAll("[data-share-menu]").forEach(function (menu) {
      menu.addEventListener("toggle", function () {
        const card = menu.closest(".visual-card");
        if (card) {
          card.classList.toggle("share-open", menu.open);
        }
      });
    });
  });

  document.addEventListener("click", async function (event) {
    const nativeButton = event.target.closest("[data-share-native]");
    const copyLinkButton = event.target.closest("[data-copy-link]");
    const copyTextButton = event.target.closest("[data-copy-share-text]");
    const target = nativeButton || copyLinkButton || copyTextButton;
    if (!target) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    const menu = target.closest("[data-share-menu]");
    try {
      if (nativeButton) {
        await shareViaNativeOrFallback(payloadFromElement(nativeButton));
      } else if (copyLinkButton) {
        await copyToClipboard(absoluteUrl(copyLinkButton.dataset.shareUrl));
        showCopied(copyLinkButton, "Enllac copiat");
      } else if (copyTextButton) {
        await copyToClipboard(payloadFromElement(copyTextButton).text);
        showCopied(copyTextButton, "Text copiat");
      }
    } catch (error) {
      showCopied(target, "No s'ha pogut copiar");
    } finally {
      if (menu) {
        window.setTimeout(function () {
          menu.open = false;
        }, 450);
      }
    }
  });

  window.SelectoraShare = {
    buildPublicItemUrl,
    buildPublicCollectionUrl,
    buildPublicChannelUrl,
    shareViaNativeOrFallback,
    copyToClipboard,
    buildItemShareText,
    buildCollectionShareText,
    buildChannelShareText,
    buildSiteShareText,
  };
})();
