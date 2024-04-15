# LNURL for phoenixd ⚡️

👾 Also available on the P2P Git forge, [Radicle](https://radicle.xyz) at `rad:z4G6sJdYgCqKswKnrBbYgn9QaHBqh`

**🚧 NOTE This is new software, loss of funds and other mishaps are likely 🚧**

A simple wrapper for [ACINQ/phoenixd](https://github.com/ACINQ/phoenixd) that supports basic [LNURL](https://github.com/lnurl/luds) so you can self-host your lightning address with near-minimum effort 💯.

Supports **one** user with a human-readable LNURL like `lightning:satoshi@gmx.com`, as well as LNURL LUD-06 (the long Bech encoded `lightning:LNURL1blahblah` kind) *and* a snazzy [tip webpage at `/lnurl`](https://1f52b.xyz/lnurl):

![Tip page screenshots (web and phone)](./img/screenshot.jpg)

The idea is that you can run your own `phoenixd` instance and use it to receive Lightning tips, Zaps on Nostr and more-generally small usually un-requested payments.
This is intended for a single person to use, because you like self-hosting and owning your own stuff.

If you're looking for something more complex, like an eCommerce Lightning solution, this is almost certainly going to be too simple for you;
check out [LNBits](https://lnbits.com/) or [BTCPay Server](https://btcpayserver.org/) and other things like those.
Note that LNBits will support phoenixd [soon™️](https://github.com/lnbits/lnbits/pull/2362).


## Compatibility

Developed against `phoenixd version 0.1.4-04bd430` (and `0.1.3-d805f81`); also note that phoenixd is also new software and future releases may break things.

Currently tested on MacOS and Linux; YMMV on other UNIXes, and on Windows.


### Supported LNURL LUDs:

 * [LUD-01](https://github.com/lnurl/luds/blob/luds/01.md): Base LNURL encoding and decoding
 * [LUD-06](https://github.com/lnurl/luds/blob/luds/06.md): `payRequest` base spec.
 * [LUD-16](https://github.com/lnurl/luds/blob/luds/16.md): Paying to static internet identifiers *(email-like addresses)*.

### Supported Nostr NIPs:

 * [NIP-01](https://github.com/nostr-protocol/nips/blob/master/01.md) Basic protocol flow description
 * [NIP-05](https://github.com/nostr-protocol/nips/blob/master/05.md): Mapping Nostr keys to DNS-based internet identifiers (as a NIP-5 server, optional)
 * [NIP-57](https://github.com/nostr-protocol/nips/blob/master/57.md): Lightning Zaps (receive only)


## Docker Setup

A docker container with the latest release is available from `ghcr.io/angusp/phoenixd-lnurl:latest`.

Each of the settings in [`phoenixd-lnurl.env`](./phoenixd-lnurl.env.example) can be set using environment variables passed to the container, which is probably the easiest way to set this up.

As you'll also need to run phoenixd and some sort of webserver, so using **Docker compose** is likely easiest way to get all of the required pieces running: [./examples/docker-compose.yml](./examples/docker-compose.yml):

```shell
docker-compose -f examples/docker-compose.yml up
```

To run just the phoenixd-lnurl image instead:

```shell
# Pull the image:
docker pull ghcr.io/angusp/phoenixd-lnurl:latest
docker tag ghcr.io/angusp/phoenixd-lnurl:latest phoenixd-lnurl:latest
# or build the image from a locally checked-out repo:
docker build . -t phoenixd-lnurl:latest

docker run -p 8000:8000 \
    # Pass config as environment variables: (See phoenixd-lnurl.env.example for the list)
    --env USERNAME=satoshi \
    --env PHOENIXD_URL="http://_:hunter2@127.0.0.1:9740" \
    --env LNURL_HOSTNAME=example.com \
    # Or pass in a .env file:
    --env-file phoenixd-lnurl.env \
    -it phoenixd-lnurl:latest
```

 * `localhost:8000/lnurl` Tip webpage as in the screenshot above
 * `localhost:8000/.well-known/lnurlp/<USERNAME>` LNURL payRequest endpoint (LUD-16) for `<USERNAME>@<LNURL_HOSTNAME>`
 * `localhost:8000/lnurlp/<USERNAME>` LNURL payRequest endpoint (LUD-06)
 * `localhost:8000/lnurlp/<USERNAME>/callback?amount=<AMOUNT_MSAT>` LNURL payRequest callback (LUD-06 and LUD-16)
 * `localhost:8000/.well-known/nostr.json` (Optional) Nostr NIP-5 server for `<USERNAME>@<LNURL_HOSTNAME>`
 * **⚠️ INTERNAL ONLY** `localhost:8000/phoenixd-webhook` -- you need to add this to your `~/.phoenixd/phoenix.conf` for Nostr Zaps to work correctly. ‼️ DO NOT make this publicly accessible ‼️
 * **Note** `localhost:8000/` and any other path will give you an `ERROR` -- that's supposed to happen, as it isn't a LNURL that **pheonixd-lnurl** understands 😉


## Non-Docker Setup

If you haven't got it already, install [phoenixd](https://github.com/ACINQ/phoenixd/releases) so you have `phoenixd` and `phoenix-cli` in your path.

See `.tool-versions` for the currently used version of Python.
We're also using `pip-tools` to manage dependencies.

```shell
# Strongly recommend you create a python environment first:
python -m venv env
. env/bin/activate

# manually install pip-tools:
pip install pip-tools

# then sync the dependencies:
pip-sync
```


Using this example `~/.phoenix/phoenix.conf` for demonstration purposes:

```conf
chain=testnet
http-password=hunter2
http-bind-port=9740
auto-liquidity=2m
webhook=http://localhost:8000/phoenixd-webhook
```

For **production** use, you can *just* install and run `phoenixd` for the first time;
it will create `~/.phoenix` with sane defaults and an auto-generated http password.

You'll then need to configure `phoenixd-lnurl` itself. Copy `phoenixd-lnurl.env.example` to `phoenixd-lnurl.env` and edit it with the values you want; info on each option is given in the template.

Importantly:

 1. `PHOENIXD_URL` needs to set so that this app can talk to your phoenixd.
    * Note that the `http-password` from phoenixd's config has to be in this URL
 2. `LNURL_HOSTNAME` must be the public domain you're serving from. You need to have HTTPS set up for LNURL to work.

Now you're ready to run:

```shell
# start the phoenixd-lnurl server:
./run.sh
```

 * `localhost:8000/lnurl` Tip webpage as in the screenshot above
 * `localhost:8000/.well-known/lnurlp/<USERNAME>` LNURL payRequest endpoint (LUD-16) for `<USERNAME>@<LNURL_HOSTNAME>`
 * `localhost:8000/lnurlp/<USERNAME>` LNURL payRequest endpoint (LUD-06)
 * `localhost:8000/lnurlp/<USERNAME>/callback?amount=<AMOUNT_MSAT>` LNURL payRequest callback (LUD-06 and LUD-16)
 * `localhost:8000/.well-known/nostr.json` (Optional) Nostr NIP-5 server for `<USERNAME>@<LNURL_HOSTNAME>`
 * **⚠️ INTERNAL ONLY** `localhost:8000/phoenixd-webhook` -- you need to add this to your `~/.phoenixd/phoenix.conf` for Nostr Zaps to work correctly. ‼️ DO NOT make this publicly accessible ‼️
 * **Note** `localhost:8000/` and any other path will give you an `ERROR` -- that's supposed to happen, as it isn't a LNURL that **pheonixd-lnurl** understands 😉

To deploy, you probably want something to manage **phoenixd-lnurl** as a service, rather than running it directly.
Some example config is provided to help with this:

**Example configuration**:

* Docker compose: [./examples/docker-compose.yml](./examples/docker-compose.yml)
* Nginx: [./examples/nginx.conf](./examples/nginx.conf)
* Systemd: [./examples/phoenixd-lnurl.service](./examples/phoenixd-lnurl.service)

(**Note**: You may also hit a selinux issue if using nginx, try `setsebool -P httpd_can_network_connect true`)


---

## Developing

There's a set of additional dev requirements you need to install for tests to work and stuff:

Life will be easier if you also have [`just`](https://github.com/casey/just) installed, but you can get by without it.

```shell
just install
# Or, manually:
# $ pip-sync requirements-dev.txt

# Run just just to see other options
just

# API docs (paths for phoenixd-lnurl with try-it-out buttons):
just docs
```

If you are stubborn, you can also forego installing `pip-tools` and use a regular `pip install -r requirements-dev.txt`, but changes to requirements must be made using the pip-tools tooling.

Using a tool like [`ngrok`](https://ngrok.com/) to proxy your local server (and optionally phoenixd) to the internet is handy, as LNURL requires `https` for clearnet.

Getting a decent testnet Lightning wallet with all the bells and whistles is also a bit of a pain.
I found [Zeus](https://zeusln.com/) worked well using the *Embedded LND node* on *testnet* without much fuss -- caveat being that you can't *also* have a mainnet embedded LND configured.
Running a second phoenixd would also work, but it doesn't support LNURL so you'd have to copy-paste invoices and manually call phoenixd-lnurl.

Once you have that, you'll have to hunt for a testnet faucet to get some testnet sats.

When ready:

```shell
# Make sure you've already got `phoenixd` running!
just serve
```


### Roadmap to v1.0

- [X] Just receive LNURL LUD-16 payments (zaps)
- [X] Simple "zap me" QR code and copyable `lightning:LNURL1...` link webpage LUD-16
- [X] Provide sample Docker image
- [X] Provide sample docker-compose config (credit @sethforprivacy)
- [X] Provide sample Nginx config
- [X] Provide sample Systemd service definition
- [ ] Basic CI (check normal install, dev install)
- [X] Provide sample Traefik config (in the docker-compose example) (credit @sethforprivacy)
- [ ] Support `.onion` hosting (HTTPS is assumed in a few places), needed for self-hosting on things like Umbrel
- [ ] Support [LUD-18: Payer identity in `payRequest` protocol](https://github.com/lnurl/luds/blob/luds/18.md)
- [ ] Support configurable URL prefix for the app for people that might have collisions or don't want to host at `/` (or do this in nginx conf)
- [ ] Support actual Nostr Zaps [NIP-57: Lightning Zaps](https://github.com/nostr-protocol/nips/blob/master/57.md)
- [ ] Support [NIP-47: Nostr Wallet Connect](https://github.com/nostr-protocol/nips/blob/master/47.md)


### Later Roadmap

- [ ] Notify when payments are received (Nostr DM?)
- [ ] Support some kind of withdrawal mechanism (via Nostr DM?) instead of needing manual `phoenix-cli` use to get money out
- [ ] Also optionally be a Nostr NIP-05 server
- [ ] Support multiple usernames
- [ ] (maybe-scope-creep) auto-zap content you interact with/like on Nostr if funds are available


---

## License ⚖️

This work is dual-licensed under Apache 2.0 and BSD-2-Clause.
You can choose between one of them if you use this work.

`SPDX-License-Identifier: Apache-2.0 OR BSD-2-Clause`
