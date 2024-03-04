- Go to https://www.hoyolab.com/home, make sure you are logged into your HoyoLAB account. While on the HoyoLAB page,
type "java" in the address bar, and paste the following snippet right after it (WITHOUT a space):

```js
script:check = document.cookie.includes('ltoken') && document.cookie.includes('ltuid') || alert('Please logout and log back in before trying again, cookie is currently expired/invalid!');  var ltoken = document.cookie.match(/(?<=ltoken=)[^;]*/); var ltuid = document.cookie.match(/(?<=ltuid=)[^;]*/); var output = "ltoken:" + ltoken + " ltuid:" + ltuid; cookie = document.cookie; check && document.write(`<p>${output}</p><br><button onclick="navigator.clipboard.writeText('${output}')">Click here to copy!</button><br>`)
```

- Press enter. You should be seeing a page that shows your ltoken and ltuid cookies. Click on the "Click here to copy!" button to copy those for use in registration.

<h1>Register for Genshin Impact</h1>
_resin register ltoken:(ltoken) ltuid:(ltuid) genshinuid:(your genshin UID)

<h1>Register for Honkai: Star Rail</h1>
_stamina register ltoken:(ltoken) ltuid:(ltuid) hsruid:(your HSR UID)

<h1>Register for both Genshin Impact <i>and</i> Honkai: Star Rail</h1>
_stamina register ltoken:(ltoken) ltuid:(ltuid) genshinuid:(your genshin UID) hsruid:(your HSR UID)

**or**

_resin register ltoken:(ltoken) ltuid:(ltuid) genshinuid:(your genshin UID) hsruid:(your HSR UID)

- If at any point you have entered faulty data (wrong cookie, uid etc.) you may use the register commands 
for each respective game again to fix those issues.
