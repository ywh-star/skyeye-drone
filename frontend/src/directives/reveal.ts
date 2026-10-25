import type { Directive, DirectiveBinding } from 'vue'

/**
 * 自定义指令 v-reveal：元素进入视口后渐入。
 */
type RevealEl = HTMLElement & { __revealObserver?: IntersectionObserver }

const observer = new IntersectionObserver(
  (entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed')
        observer.unobserve(entry.target)
      }
    }
  },
  { threshold: 0.12 },
)

function apply(el: RevealEl, binding: DirectiveBinding<number | undefined>) {
  el.classList.add('reveal')
  if (binding.value) el.style.transitionDelay = `${binding.value}ms`
  observer.observe(el)
}

export const vReveal: Directive<RevealEl, number | undefined> = {
  mounted(el, binding) {
    apply(el, binding)
  },
  unmounted(el) {
    observer.unobserve(el)
  },
}
