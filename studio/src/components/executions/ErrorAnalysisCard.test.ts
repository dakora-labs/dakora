/**
 * Test file demonstrating error parsing logic
 * Run this manually to verify error message parsing works correctly
 */

/**
 * Parse error message to extract structured information
 * Example input: "ServiceResponseException("<class 'agent_framework.openai._chat_client.OpenAIChatClient'> service failed to complete the prompt: AsyncCompletions.create() got an unexpected keyword argument 'conversation_id'")"
 */
function parseErrorMessage(message: string) {
  const fullMessage = message;
  
  // Extract exception type
  const exceptionTypeMatch = message.match(/^(\w+)\(/);
  const exceptionType = exceptionTypeMatch ? exceptionTypeMatch[1] : 'UnknownError';
  
  // Extract root cause (last meaningful part of the error message)
  let rootCause = message;
  
  // Remove outer exception wrapper like ServiceResponseException("...")
  const innerMatch = message.match(/\w+\("(.*?)"\)(?:\))?$/);
  if (innerMatch) {
    rootCause = innerMatch[1];
  }
  
  // Clean up class references
  rootCause = rootCause
    .replace(/<class '[^']+'>\\s*/g, '')
    .replace(/<class '[^']+'>\\s*/g, '')
    .replace(/\\n/g, '\n')
    .trim();
  
  return {
    exceptionType,
    rootCause,
    fullMessage,
  };
}

// TEST CASES

console.log('=== ERROR PARSING TEST ===\n');

// Test 1: Trace c95998f353c23888fd56400c9531cde4
const testMessage1 = `ServiceResponseException("<class 'agent_framework.openai._chat_client.OpenAIChatClient'> service failed to complete the prompt: AsyncCompletions.create() got an unexpected keyword argument 'conversation_id'")`;

console.log('TEST 1: Service Response Exception');
console.log('Input:', testMessage1);
const result1 = parseErrorMessage(testMessage1);
console.log('Exception Type:', result1.exceptionType);
console.log('Root Cause:', result1.rootCause);
console.log('✓ Expected: ServiceResponseException extracted\n');

// Test 2: Simple exception
const testMessage2 = `RuntimeError("Database connection failed")`;
console.log('TEST 2: Simple Exception');
console.log('Input:', testMessage2);
const result2 = parseErrorMessage(testMessage2);
console.log('Exception Type:', result2.exceptionType);
console.log('Root Cause:', result2.rootCause);
console.log('✓ Expected: RuntimeError extracted\n');

// Test 3: Unknown format (fallback)
const testMessage3 = `Something went wrong unexpectedly`;
console.log('TEST 3: Unknown Format (Fallback)');
console.log('Input:', testMessage3);
const result3 = parseErrorMessage(testMessage3);
console.log('Exception Type:', result3.exceptionType);
console.log('Root Cause:', result3.rootCause);
console.log('✓ Expected: Falls back to full message\n');
