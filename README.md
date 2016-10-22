Confluence-dns
==============

Generates Bind9 DNS-zones from a Confluence tables. Use with caution! This script is not very well tested and may break your DNS-zones.


Setup
=====


Create a page to Confluence with at least following tables:

A table containing subnets and other DNS-stuff.

| ZONE | master | hostmaster | servers |
|---------|--------|----|----|
| example.com | ns1.example.com | hostmaster@example.com | ns1.example.com ns2.example.com |
| 0.0.10.in-addr.arpa | ns1.example.com | hostmaster@example.com | ns1.example.com ns2.example.com |

And following table containing addresses.

<table>
  <tr>
    <td>Name</td>
    <td>A</td>
    <td>AAAA</td>
    <td>CNAME</td>
    <td>SRV</td>
    <td>Description</td>

  </tr>
  <tr>
    <td colspan="5"># network</td>
  </tr>
  <tr>
    <td>example</td>
    <td>10.0.0.5</td>
    <td></td>
    <td>foo.example.com</td>
    <td></td>
    <td>Example row</td>
  </tr>
</table>

Setup an Confluence user with permission to read the page just created.

Configure username and other things to config.py

    cp config.py.example config.py
    vi config.py

Also setup a virtualenv and install required packages

    virtualenv env --python=python3
    . env/bin/activate
    pip install -r requirements.txt


Usage
====


    . env/bin/activate
    python dns-updater.py


License
========

The MIT License (MIT)

Copyright (c) 2015 Antti Jaakkola

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
