(function () {
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function () {});
    });
  }
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
    return true;
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
    if (openDrawer(targetId)) {
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
  };
})();
