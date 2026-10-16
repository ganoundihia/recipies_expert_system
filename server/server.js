const path = require('path');
const { execFile } = require('child_process');
const express = require('express');
const cors = require('cors');

const PORT = Number(process.env.PORT) || 7000;
const CLIENT_ORIGIN = process.env.CLIENT_ORIGIN || 'http://localhost:3000';
const PYTHON = process.env.EXPERT_SYSTEM_PYTHON ||(process.platform === 'win32' ? 'python' : 'python3');
const EXPERT_SYSTEM = path.join(__dirname, 'expert_system.py');
const INFERENCE_TIMEOUT_MS = 10000;

/**
 * Runs the Python expert system on the user's choices.
 * Resolves with `{ recipe, trace }`, rejects with an Error carrying an HTTP `status`.
 */
function runExpertSystem(choices) {
    return new Promise((resolve, reject) => {
        execFile(
            PYTHON,
            [EXPERT_SYSTEM, JSON.stringify(choices)],
            { timeout: INFERENCE_TIMEOUT_MS, windowsHide: true },
            (error, stdout, stderr) => {
                let output;
                try {
                    output = JSON.parse(stdout);
                } catch {
                    const failure = new Error(stderr || (error && error.message) || 'Invalid expert system output');
                    failure.status = 500;
                    return reject(failure);
                }
                if (output.error) {
                    const failure = new Error(output.error);
                    failure.status = 400;
                    return reject(failure);
                }
                resolve(output);
            }
        );
    });
}

const app = express();

app.use(cors({ origin: CLIENT_ORIGIN, methods: ['GET', 'POST'] }));
app.use(express.json());

app.get('/health', (req, res) => {
    res.json({ status: 'ok' });
});

app.post('/recommend', async (req, res) => {
    const { flour, fat, flavor } = req.body || {};
    try {
        const result = await runExpertSystem({ flour, fat, flavor });
        if (!result.recipe) {
            return res.status(404).json({ error: 'No recipe matches these ingredients.' });
        }
        res.json(result);
    } catch (error) {
        if (error.status !== 400) {
            console.error('Expert system failure:', error.message);
        }
        res.status(error.status || 500).json({
            error: error.status === 400 ? error.message : 'Internal server error',
        });
    }
});

if (require.main === module) {
    app.listen(PORT, () => {
        console.log(`Recipe expert system API listening on http://localhost:${PORT}`);
    });
}

module.exports = app;
