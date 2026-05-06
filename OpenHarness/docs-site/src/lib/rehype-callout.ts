import { visit } from 'unist-util-visit';
// @ts-ignore
import { h } from 'hastscript';

const CALLOUT_TYPES: Record<string, { class: string; icon: string }> = {
  info: {
    class: 'callout callout-info',
    icon: `<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`,
  },
  warning: {
    class: 'callout callout-warning',
    icon: `<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>`,
  },
  error: {
    class: 'callout callout-error',
    icon: `<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`,
  },
  tip: {
    class: 'callout callout-tip',
    icon: `<svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>`,
  },
};

/**
 * Remark/rehype plugin to transform `> [!type]` blockquotes into styled callout divs.
 * Usage: > [!info] Your message here
 */
export function rehypeCallout() {
  return (tree: any) => {
    visit(tree, 'element', (node: any, index: number | undefined, parent: any) => {
      if (node.tagName !== 'blockquote' || index === undefined || !parent) return;

      const firstPara = node.children?.find(
        (c: any) => c.tagName === 'p' || c.tagName === 'element'
      );
      if (!firstPara) return;

      const firstText = firstPara.children?.find(
        (c: any) => c.type === 'text' || (c.tagName === 'element' && c.children?.some((cc: any) => cc.type === 'text'))
      );
      if (!firstText) return;

      let text = '';
      if (firstText.type === 'text') {
        text = firstText.value || '';
      } else {
        const t = firstText.children?.find((c: any) => c.type === 'text');
        text = t?.value || '';
      }

      const match = text.match(/^\[!(info|warning|error|tip)\]\s*/i);
      if (!match) return;

      const type = match[1].toLowerCase();
      const config = CALLOUT_TYPES[type];
      if (!config) return;

      // Build callout div
      const calloutDiv = h('div', { className: config.class }, [
        h('div', { className: 'flex items-start gap-3' }, [
          h('div', { className: 'mt-0.5', innerHTML: config.icon }),
          h('div', { className: 'flex-1 min-w-0' }, node.children.map((child: any) => {
            // Remove the [!type] prefix from first paragraph
            if (child === firstPara) {
              return {
                ...child,
                children: child.children.map((c: any) => {
                  if (c.type === 'text' && c.value) {
                    return { ...c, value: c.value.replace(/^\[!(info|warning|error|tip)\]\s*/i, '') };
                  }
                  return c;
                }),
              };
            }
            return child;
          })),
        ]),
      ]);

      parent.children.splice(index, 1, calloutDiv);
    });
  };
}
