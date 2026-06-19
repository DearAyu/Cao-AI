# Video Prompt Input Adjustments

## Scope

Update only the video creation prompt field. The image prompt field and preset controls remain unchanged.

## Behavior

- Rename the field label from `影棚提示词` to `提示词`.
- Increase the maximum input length from 1500 to 2500 characters and keep the visible character counter.
- On the first focus, clear the initial built-in prompt only when the field still exactly matches that default value.
- Never clear user-entered text or text selected from a preset on later focuses.

## Implementation

Keep the default prompt as a named constant and track whether the initial focus behavior has run. A focus handler performs the guarded clear. This keeps the change local to `App.vue` and preserves the existing form data flow.

## Verification

Component tests will cover the label, new length limit, first-focus clear, and preservation of edited text. The frontend test suite and production build must pass, followed by browser verification at the existing mobile-width viewport.
