# Getting Started with Create React App

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## Local development in this repo

The script notes below are the Create React App defaults and do not match this project. It runs with
`npm start` on **port 3800** (see `vite.config.ts`), and Vite proxies `/api` and `/ws` to the backend on
`:8000`.

The realtime socket is the part that bites, and only measured statements belong here. `vite.config.ts`
sets `envDir: '..'`, so the env FILE Vite reads is the REPO ROOT's `.env` - this directory holds only
`.env.sample` - and **a shell export of `VITE_WS_URL` WINS over that file's value**, because Vite gives
variables already present when it runs the highest priority. The socket URL a dev client ends up with is
decided by the CONFIG's env loading, measured by reading the injected object itself (the investigation is
filed at `.openrig/agenthub-seats/4genthub-min/VITE-ENV-INVESTIGATION.md`): the first line of the
transformed `src/config/environment.ts` IS `import.meta.env`, and two dev servers with the same source
file differ - one loaded the parent env and carried `VITE_WS_URL`, the other set no `envDir`, so Vite used
its default (this directory, which holds only `.env.sample`) and injected only the process environment's
variables, with the URL absent. So the client's read is correct and its fallback to the page origin is the
correct consequence: **the value never arrived** rather than being discarded, and in that state the `/ws`
proxy above is what carries the socket to the API. Without it, the dev server's own websocket server
accepts the upgrade and the UI reports **Live with no backend behind it**. For any future instance, one
command settles it: fetch the transformed config module from the running dev server
(`/src/config/environment.ts`) and read line one - the injected object is literally there and a missing
key is visible without inference. Which config the original observing run used is not provable from here.

## Available Scripts

In the project directory, you can run:

### `pnpm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

The page will reload if you make edits.\
You will also see any lint errors in the console.

### `pnpm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/ai_docs/running-tests) for more information.

### `pnpm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/ai_docs/deployment) for more information.

### `pnpm run eject`

**Note: this is a one-way operation. Once you `eject`, you can’t go back!**

If you aren’t satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you’re on your own.

You don’t have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn’t feel obligated to use this feature. However we understand that this tool wouldn’t be useful if you couldn’t customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/ai_docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).
