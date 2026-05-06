// Complete implementation of condition-based waiting utilities

export function waitForEvent(
  threadManager, threadId, eventType, timeoutMs = 5000
): Promise {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();
    const check = () => {
      const events = threadManager.getEvents(threadId);
      const event = events.find((e) => e.type === eventType);
      if (event) resolve(event);
      else if (Date.now() - startTime > timeoutMs)
        reject(new Error(`Timeout waiting for ${eventType}`));
      else setTimeout(check, 10);
    };
    check();
  });
}

export function waitForEventCount(
  threadManager, threadId, eventType, count, timeoutMs = 5000
): Promise {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();
    const check = () => {
      const events = threadManager.getEvents(threadId);
      const matching = events.filter((e) => e.type === eventType);
      if (matching.length >= count) resolve(matching);
      else if (Date.now() - startTime > timeoutMs)
        reject(new Error(`Timeout waiting for ${count} events`));
      else setTimeout(check, 10);
    };
    check();
  });
}
