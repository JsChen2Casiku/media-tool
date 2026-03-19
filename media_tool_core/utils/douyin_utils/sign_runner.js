const fs = require("fs");
const vm = require("vm");

function main() {
  const [, , scriptPath, functionName, encodedArgs] = process.argv;

  if (!scriptPath || !functionName) {
    throw new Error("Usage: node sign_runner.js <scriptPath> <functionName> <jsonArgs>");
  }

  const args = encodedArgs ? JSON.parse(encodedArgs) : [];
  const code = fs.readFileSync(scriptPath, "utf8");

  const sandbox = {
    console,
    Date,
    Math,
    JSON,
    Array,
    ArrayBuffer,
    Uint8Array,
    Uint16Array,
    Uint32Array,
    Int8Array,
    Int16Array,
    Int32Array,
    String,
    Number,
    Boolean,
    Object,
    RegExp,
    parseInt,
    parseFloat,
    encodeURIComponent,
    decodeURIComponent,
    setTimeout,
    clearTimeout,
  };

  sandbox.window = sandbox;
  sandbox.self = sandbox;
  sandbox.global = sandbox;
  sandbox.globalThis = sandbox;

  vm.createContext(sandbox);
  vm.runInContext(code, sandbox, { filename: scriptPath });

  const target = sandbox[functionName];
  if (typeof target !== "function") {
    throw new Error(`Function not found: ${functionName}`);
  }

  const result = target(...args);
  process.stdout.write(typeof result === "string" ? result : JSON.stringify(result));
}

main();
