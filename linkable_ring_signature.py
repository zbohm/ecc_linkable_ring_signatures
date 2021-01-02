#! /usr/bin/env python
#
# Provide an implementation of Linkable Spontaneus Anonymous Group Signature
# over elliptic curve cryptography.
#
# Implementation of cryptographic scheme from PDF [Linkable Spontaneous Anonymous Group Signature for Ad Hoc Groups](https://eprint.iacr.org/2004/027.pdf)
# from Joseph K. Liu, Victor K. Wei and Duncan S. Wong.
#
# Written in 2017 by Fernanddo Lobato Meeser and placed in the public domain.
#
# Note: To show as a literar code documentation compile this code by [pycoo](https://pypi.org/project/Pycco/).

import os
import hashlib
import functools
import ecdsa

from ecdsa.util import randrange
from ecdsa.ecdsa import curve_secp256k1
from ecdsa.curves import SECP256k1
from ecdsa import numbertheory


def ring_signature(siging_key, key_idx, M, y, G=SECP256k1.generator, hash_func=hashlib.sha3_256):
    """
    # Make a ring signature

    Generates a ring signature for a message given a specific set of
    public keys and a signing key belonging to one of the public keys
    in the set.

    ### Params:

    signing_key: (int) The with which the message is to be anonymously signed.

    key_idx: (int) The index of the public key corresponding to the signature
        private key over the list of public keys that compromise the signature.

    M: (str) Message to be signed.

    y: (list) The list of public keys which over which the anonymous signature
        will be compose.

    G: (ecdsa.ellipticcurve.Point) Base point for the elliptic curve.

    hash_func: (function) Cryptographic hash function that recieves an input
        and outputs a digest.

    ### Returns:

    Signature (c_0, s, Y):

    c_0: Initial value to reconstruct signature.
    s = vector of randomly generated values with encrypted secret to
        reconstruct signature.
    Y = Link for current signer.
    """

    # # 4 A LSAG Signature Scheme

    # Let *G* = ⧼g⧽ be a group of prime order *q* such that the underlying discrete
    # logarithm problem is intractable. Let *H<sub>1</sub>* : {0, 1}∗ → *Z<sub>q</sub>* and *H<sub>2</sub>* : {0, 1}∗ → *G*
    # be some statistically independent cryptographic hash functions. For *i = 1, · · ·, n,*
    # each user *i* has a distinct public key *y<sub>i</sub>* and a private key *x<sub>i</sub>* such that *y<sub>i</sub> = g<sup>x<sub>i</sub></sup>*.
    # Let *L = {y<sub>1</sub>, · · ·, y<sub>n</sub>}* be the list of *n* public keys.

    # ## 4.1 Signature Generation

    # Given message *m* ∈ {0, 1}∗, list of public key *L = {y<sub>1</sub>, · · · , y<sub>n</sub>}*, private key
    # x<sub>π</sub> corresponding to *y<sub>π</sub> 1 ≤ π ≤ n*, the following algorithm generates a LSAG
    # signature.

    n = len(y)
    c = [0] * n
    s = [0] * n

    # ### Step 1
    # Compute *h = H<sub>2</sub>(L)* and *ỹ = h<sup>x<sub>π</sub></sup>*.

    H = H2([y, M], hash_func=hash_func)
    Y = H * siging_key

    # ### Step 2
    # Pick *u ∈<sub>R</sub> Z<sub>q</sub>*, and compute
    #
    # *c<sub>π+1</sub> = H<sub>1</sub>(L, ỹ, m, g<sup>u</sup>, h<sup>u</sup>)*.

    u = randrange(SECP256k1.order)
    c[(key_idx + 1) % n] = H1([y, Y, M, G * u, H * u], hash_func=hash_func)

    # ### Step 3
    # For *i* = π+1, · · · , *n*, 1, · · · , π−1, pick *s<sub>i</sub> ∈<sub>R</sub> Z<sub>q</sub>* and compute
    #
    # *c<sub>i+1</sub> = H<sub>1</sub>(L, ỹ, m, g<sup>s<sub>i</sub></sup> y<sub>i</sub><sup>c<sub>i</sub></sup>, h<sup>s<sub>i</sub></sup> ỹ<sup>c<sub>i</sub></sup>)*.

    for i in [ i for i in range(key_idx + 1, n) ] + [i for i in range(key_idx)]:

        s[i] = randrange(SECP256k1.order)

        z_1 = (G * s[i]) + (y[i] * c[i])
        z_2 = (H * s[i]) + (Y * c[i])

        c[(i + 1) % n] = H1([y, Y, M, z_1, z_2], hash_func=hash_func)

    # ### Step 4
    # Compute *s<sub>π</sub>* = *u − x<sub>π</sub>c<sub>π</sub>* mod *q*.

    s[key_idx] = (u - siging_key * c[key_idx]) % SECP256k1.order

    # The signature is *σ<sub>L</sub>(m) = (c<sub>1</sub>, s<sub>1</sub> , · · ·, s<sub>n</sub>, ỹ)*.

    return (c[0], s, Y)


def verify_ring_signature(message, y, c_0, s, Y, G=SECP256k1.generator, hash_func=hashlib.sha3_256):
    """
    # Verify the ring signature

    Verifies if a valid signature was made by a key inside a set of keys.

    ### Params:

    message: (str) message whos' signature is being verified.

    y: (list) set of public keys with which the message was signed.

    #### Signature:

    c_0: (int) initial value to reconstruct the ring.

    s: (list) vector of secrets used to create ring.

    Y = (int) Link of unique signer.

    G: (ecdsa.ellipticcurve.Point) Base point for the elliptic curve.

    hash_func: (function) Cryptographic hash function that recieves an input
        and outputs a digest.

    ### Returns:

    Boolean value indicating if signature is valid.
    """
    n = len(y)
    c = [c_0] + [0] * (n - 1)

    H = H2([y, message], hash_func=hash_func)

    for i in range(n):
        z_1 = (G * s[i]) + (y[i] * c[i])
        z_2 = (H * s[i]) + (Y * c[i])

        if i < n - 1:
            c[i + 1] = H1([y, Y, message, z_1, z_2], hash_func=hash_func)
        else:
            return c_0 == H1([y, Y, message, z_1, z_2], hash_func=hash_func)

    return False


def map_to_curve(x, P=curve_secp256k1.p()):
    """
    Maps an integer to an elliptic curve.

    Using the try and increment algorithm, not quite
    as efficient as I would like, but c'est la vie.

    ### Params:

    x: (int) number to be mapped into E.

    P: (ecdsa.curves.curve_secp256k1.p) Modulo for elliptic curve.

    ### Returns:
    (ecdsa.ellipticcurve.Point) Point in Curve
    """
    x -= 1
    y = 0
    found = False

    while not found:
        x += 1
        f_x = (x * x * x + 7) % P

        try:
            y = numbertheory.square_root_mod_prime(f_x, P)
            found = True
        except Exception as e:
            pass

    return ecdsa.ellipticcurve.Point(curve_secp256k1, x, y)


def H1(msg, hash_func=hashlib.sha3_256):
    """
    Return an integer representation of the hash of a message. The
    message can be a list of messages that are concatenated with the
    concat() function.

    ### Params:

    msg: (str or list) message(s) to be hashed.

    hash_func: (function) a hash function which can recieve an input
        string and return a hexadecimal digest.

    ### Returns:
    Integer representation of hexadecimal digest from hash function.
    """
    return int('0x'+ hash_func(concat(msg)).hexdigest(), 16)


def H2(msg, hash_func=hashlib.sha3_256):
    """
    Hashes a message into an elliptic curve point.

    ### Params:

    msg: (str or list) message(s) to be hashed.

    hash_func: (function) Cryptographic hash function that recieves an input
        and outputs a digest.

    ### Returns:
    ecdsa.ellipticcurve.Point to curve.
    """
    return map_to_curve(H1(msg, hash_func=hash_func))


def concat(params):
    """
    Concatenates a list of parameters into a bytes. If one
    of the parameters is a list, calls itself recursively.

    ### Params:
    params: (list) list of elements, must be of type:
        - int
        - list
        - str
        - ecdsa.ellipticcurve.Point

    ### Returns:
    concatenated bytes of all values.
    """
    n = len(params)
    bytes_value = [0] * n

    for i in range(n):

        if type(params[i]) is int:
            bytes_value[i] = params[i].to_bytes(32, 'big')
        if type(params[i]) is list:
            bytes_value[i] = concat(params[i])
        if type(params[i]) is ecdsa.ellipticcurve.Point:
            bytes_value[i] = params[i].x().to_bytes(32, 'big') + params[i].y().to_bytes(32, 'big')
        if type(params[i]) is str:
            bytes_value[i] = params[i].encode()

        if bytes_value[i] == 0:
            bytes_value[i] = params[i].x().to_bytes(32, 'big') + params[i].y().to_bytes(32, 'big')

    return functools.reduce(lambda x, y: x + y, bytes_value)


def stringify_point(p):
    """
    Represents an elliptic curve point as a string coordinate.

    ### Params:
    p: ecdsa.ellipticcurve.Point - Point to represent as string.

    ### Returns:
    (str) Representation of a point (x, y)
    """
    return '{},{}'.format(p.x(), p.y())


def stringify_point_js(p):
    """
    Represents an elliptic curve point as a string coordinate, the
    string format is javascript so other javascript scripts can
    consume this.

    ### Params:
    p: ecdsa.ellipticcurve.Point - Point to represent as string.

    ### Returns:
    (str) Javascript string representation of a point (x, y)
    """
    return 'new BigNumber("{}"), new BigNumber("{}")'.format(p.x(), p.y())


def export_signature(y, message, signature, foler_name='./data', file_name='signature.txt'):
    """Exports a signature to a specific folder and filename provided.

    The file contains the signature, the ring used to generate signature
    and the message being signed.
    """
    if not os.path.exists(foler_name):
        os.makedirs(foler_name)

    arch = open(os.path.join(foler_name, file_name), 'w')
    S = ''.join(map(lambda x: str(x) + ',', signature[1]))[:-1]
    Y = stringify_point(signature[2])

    dump = '{}\n'.format(signature[0])
    dump += '{}\n'.format(S)
    dump += '{}\n'.format(Y)

    arch.write(dump)

    pub_keys = ''.join(map(lambda yi: stringify_point(yi) + ';', y))[:-1]
    data = '{}\n'.format(''.join([ '{},'.format(m) for m in message])[:-1])
    data += '{}\n,'.format(pub_keys)[:-1]

    arch.write(data)
    arch.close()


def export_private_keys(s_keys, foler_name='./data', file_name='secrets.txt'):
    """Exports a set  of private keys to a file.

    Each line in the file is one key.
    """
    if not os.path.exists(foler_name):
        os.makedirs(foler_name)

    arch = open(os.path.join(foler_name, file_name), 'w')

    for key in s_keys:
        arch.write('{}\n'.format(key))

    arch.close()


def export_signature_javascript(y, message, signature, foler_name='./data', file_name='signature.js'):
    """Exports a signatrue in javascript format to a file and folder."""
    if not os.path.exists(foler_name):
        os.makedirs(foler_name)

    arch = open(os.path.join(foler_name, file_name), 'w')

    S = ''.join(map(lambda x: 'new BigNumber("' + str(x) + '"),', signature[1]))[:-1]
    Y = stringify_point_js(signature[2])

    dump = 'var c_0 = new BigNumber("{}");\n'.format(signature[0])
    dump += 'var s = [{}];\n'.format(S)
    dump += 'var Y = [{}];\n'.format(Y)

    arch.write(dump)

    pub_keys = ''.join(map(lambda yi: stringify_point_js(yi) + ',', y))[:-1]

    data = 'var message = [{}];\n'.format(''.join([ 'new BigNumber("{}"),'.format(m) for m in message])[:-1])
    data += 'var pub_keys = [{}];'.format(pub_keys)

    arch.write(data + '\n')
    arch.close()


def main():
    number_participants = 10

    x = [ randrange(SECP256k1.order) for i in range(number_participants)]
    y = list(map(lambda xi: SECP256k1.generator * xi, x))

    message = "Every move we made was a kiss"

    i = 2
    signature = ring_signature(x[i], i, message, y)

    assert(verify_ring_signature(message, y, *signature))

if __name__ == '__main__':
    main()