# Page snapshot

```yaml
- generic [ref=e2]:
  - generic [ref=e7]:
    - generic [ref=e11]:
      - link "Sattva studio" [ref=e12] [cursor=pointer]:
        - /url: /
      - button "en" [ref=e14] [cursor=pointer]:
        - img [ref=e15]
        - generic [ref=e18]: en
    - generic [ref=e21]:
      - generic [ref=e22]:
        - paragraph [ref=e23]: ZENSTREAM ACCESS
        - heading "SATTVA" [level=2] [ref=e24]
        - paragraph [ref=e25]: Enter the stream of consciousness
      - generic [ref=e26]:
        - paragraph [ref=e27]: Choose login method
        - generic [ref=e28]:
          - generic [ref=e29]:
            - text: Email
            - textbox "Email" [ref=e30]: test_user@test.sattva.dev
          - generic [ref=e31]:
            - text: Password
            - textbox "Password" [ref=e32]: TestPass123!
          - alert [ref=e33]: Войти не удалось. Попробуйте ещё раз.
          - button "Войти" [ref=e34] [cursor=pointer]
          - paragraph [ref=e35]: Для QA и Playwright тестов
        - button "Continue with Google" [ref=e36] [cursor=pointer]:
          - img [ref=e37]
          - generic [ref=e42]: Continue with Google
        - generic [ref=e47]: or
        - button "Войти через Telegram" [ref=e48] [cursor=pointer]:
          - img [ref=e49]
          - generic [ref=e52]: Войти через Telegram
  - region "Notifications alt+T"
```