import fs from 'fs';
import path from 'path';
import * as readline from 'readline';
import dotenv from 'dotenv';
import Mistral from "@mistralai/mistralai";

// Load environment variables from a .env file
dotenv.config();

const mistralClient = new Mistral(process.env.MISTRAL_API_KEY);
const CONTEXT_FILE = "./context.txt"; // Context file
const WRITING_STYLE_FILE = "./writing_style.txt"; // Full article for style reference

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

let articleCount = 0; // Initialize article count

// Main input loop
async function processInput() {
  rl.question("Enter your query (or type 'exit' to quit):\n", async (input) => {
    if (input.toLowerCase() === 'exit') {
      rl.close();
      return;
    }

    if (!input.trim()) {
      console.log("Please enter a valid input.");
      processInput();
      return;
    }

    try {
      const context = fs.readFileSync(CONTEXT_FILE, "utf-8");
      const writingStyle = fs.readFileSync(WRITING_STYLE_FILE, "utf-8");

      if (!context) {
        console.log("No relevant context found. Proceeding with minimal guidance.");
      }

      const response = await generateChatResponse(writingStyle, context || "", input);

      // Increment the article count and write the response to a new file
      articleCount++;
      const articleFileName = `article${articleCount}.txt`;
      fs.writeFileSync(articleFileName, response, "utf-8");
      console.log(`The article has been saved to '${articleFileName}'.`);
    } catch (error) {
      console.error("An error occurred:", error.message);
    } finally {
      processInput();
    }
  });
}


// Generate a response using Mistral
async function generateChatResponse(writingStyle, context, query) {
  const currentDate = new Date().toLocaleDateString();
  const currentTime = new Date().toLocaleTimeString();
  const promptMessage = `Current Date and Time: ${currentDate}, ${currentTime}
Writing Style Example: ${writingStyle}
Context: ${context}
User Query: ${query}
Write as a paragraph in the same writing style as the Writing Style Example, using the provided context to address the query.`;

  try {
    const chatStreamResponse = await mistralClient.chatStream({
      model: 'mistral-tiny',
      messages: [
        { role: "system", content: "### You are an AI that imitates a writing style(without including any info from it) to write about the context provided. ###" },
        { role: "user", content: promptMessage }
      ],
      temperature: 0.5,
      maxTokens: 500
    });

    let finalResponse = "";
    for await (const chunk of chatStreamResponse) {
      const streamText = chunk.choices[0].delta.content;
      finalResponse += streamText;
    }

    return finalResponse;
  } catch (error) {
    console.error("Error generating response:", error.message);
    return "Sorry, I couldn't process your request.";
  }
}

// Start the input loop
processInput();
