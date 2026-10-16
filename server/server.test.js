const test = require('node:test');
const assert = require('node:assert');
const app = require('./server');

let server;
let baseUrl;

test.before(async () => {
    server = app.listen(0);
    await new Promise((resolve) => server.once('listening', resolve));
    baseUrl = `http://127.0.0.1:${server.address().port}`;
});

test.after(() => server.close());

function recommend(body) {
    return fetch(`${baseUrl}/recommend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
}

test('GET /health reports ok', async () => {
    const response = await fetch(`${baseUrl}/health`);
    assert.strictEqual(response.status, 200);
    assert.deepStrictEqual(await response.json(), { status: 'ok' });
});

test('POST /recommend returns the inferred recipe and its reasoning', async () => {
    const response = await recommend({ flour: 'cake_flour', fat: 'butter', flavor: 'vanilla' });
    assert.strictEqual(response.status, 200);
    const body = await response.json();
    assert.strictEqual(body.recipe, 'Vanilla_Cupcakes_butter');
    assert.ok(body.trace.length > 0);
});

test('POST /recommend rejects unknown ingredients with 400', async () => {
    const response = await recommend({ flour: 'rice_flour', fat: 'butter', flavor: 'vanilla' });
    assert.strictEqual(response.status, 400);
    assert.match((await response.json()).error, /flour/);
});
