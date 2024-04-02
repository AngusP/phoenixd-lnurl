# LNURL for phoenixd ⚡️

**🚧 NOTE This is new software, loss of funds and other mishaps are likely 🚧**

A simple wrapper for [ACINQ/phoenixd](https://github.com/ACINQ/phoenixd) that supports basic [LNURL](https://github.com/lnurl/luds) so you can self-host your lightning address with near-minimum effort 💯.

Supports **one** user with a human-readable LNURL like `lightning:satoshi@gmx.com`, as well as LNURL LUD-06 (the long Bech encoded `lightning:LNURL1blahblah` kind) *and* a snazzy [tip webpage at `/lnurl`](https://1f52b.xyz/lnurl):

![Tip page screenshots (web and phone)](./img/screenshot.jpg)

The idea is that you can run your own `phoenixd` instance and use it to receive Lightning tips, Zaps on Nostr and more-generally small usually un-requested payments.
This is intended for a single person to use, because they like self-hosting and owning their own stuff.

If you're looking for something more complex, like an eCommerce Lightning solution, this is almost certainly going to be too simple for you;
check out [LNBits](https://lnbits.com/) or [BTCPay Server](https://btcpayserver.org/) and other things like those.
Note that LNBits will support phoenixd [soon™️](https://github.com/lnbits/lnbits/pull/2362).


## Compatibility

Developed against `phoenixd version 0.1.3-d805f81`; also note that phoenixd is also new software and future releases may break things.

Currently tested on MacOS and Linux; YMMV on other UNIXes, and on Windows.


### Supported LNURL LUDs:

 * [LUD-01](https://github.com/lnurl/luds/blob/luds/01.md): Base LNURL encoding and decoding
 * [LUD-06](https://github.com/lnurl/luds/blob/luds/06.md): `payRequest` base spec.
 * [LUD-16](https://github.com/lnurl/luds/blob/luds/16.md): Paying to static internet identifiers *(email-like addresses)*.


## Install

*Note: Docker can be used to run this instead*

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

## Setup

Using this example `~/.phoenix/phoenix.conf` for demonstration purposes:

```conf
chain=testnet
http-password=hunter2
http-bind-port=9740
auto-liquidity=2m
max-absolute-fee=100000
```

For **production** use, you can *just* install and run `phoenixd` for the first time;
it will create `~/.phoenix` with sane defaults and an auto-generated http password.

You'll then need to configure `phoenixd-lnurl` itself. Copy `phoenixd-lnurl.env.example` to `phoenixd-lnurl.env` and edit it with the values you want; info on each option is given in the template.

Importantly:

 1. `PHOENIXD_URL` needs to set so that this app can talk to your phoenixd.
    * Note that the `http-password` from phoenixd's config has to be in this URL
 2. `LNURL_HOSTNAME` must be the public domain you're serving from. You need to have HTTPS set up for LNURL to work.

*Finally*, you're ready to go!

```shell
# start the phoenixd-lnurl server:
./run.sh
```

**Example Nginx config**

This Nginx config snippet will pass only the paths **phoenixd-lnurl** needs to work to the application:

```
server {
    # ...

    location /lnurl {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
    location /lnurlp {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
    location /.well-known/lnurlp {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }

    # ...
}
```

(May also hit selinux, try `setsebool -P httpd_can_network_connect true`)


**Example SystemD Unit**

*Note* this assumes you have installed to `/var/www/phoenixd-lnurl`.
You will also need to change `User` and `Group`.

```conf
[Unit]
Description=phoenixd-lnurlp
After=network.target

[Service]
User=<username>
Group=<group>
WorkingDirectory=/var/www/phoenixd-lnurl/src
Environment="PATH=/var/www/phoenixd-lnurl/env/bin:/usr/local/bin:/usr/bin:/usr/local/sbin:/usr/sbin"
ExecStart=/var/www/phoenixd-lnurl/run.sh

[Install]
WantedBy=multi-user.target
```


## Docker

(*Follow the **Setup** steps to configure phoenixd-lnurl first*)

```shell
docker build . -t phoenixd-lnurl

# ⚠️ This container will need to be able to connect to your `phoenixd` instance.
# To do this you might need to fiddle with the config and/or docker networking.
docker run -p 8000:8000 -it phoenixd-lnurl
```


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
- [X] Provide sample Nginx config
- [X] Provide sample Systemd service definition
- [ ] Basic CI (check normal install, dev install)
- [ ] Maybe also provide sample Traefik config
- [ ] Support configurable URL prefix for the app for people that might have collisions (or do this in nginx conf)
- [ ] Support `.onion` hosting (HTTPS is assumed in a few places), needed for self-hosting on things like Umbrel
- [ ] Support [LUD-18: Payer identity in `payRequest` protocol](https://github.com/lnurl/luds/blob/luds/18.md)


### Later Roadmap

- [ ] Notify when payments are received (Nostr DM?)
- [ ] Support some kind of withdrawal mechanism (via Nostr DM?) instead of needing manual `phoenix-cli` use to get money out
- [ ] Support actual Nostr Zaps
- [ ] Also optionally be a Nostr NIP-05 server
- [ ] Support multiple usernames
- [ ] (maybe-scope-creep) auto-zap content you interact with/like on Nostr if funds are available


---

## Tips 😘

`1f52b@1f52b.xyz` (yes, I am dogfooding) or [tip page](https://1f52b.xyz/lnurl)


---

## License ⚖️

This work is dual-licensed under Apache 2.0 and BSD-2-Clause.
You can choose between one of them if you use this work.

`SPDX-License-Identifier: Apache-2.0 OR BSD-2-Clause`
