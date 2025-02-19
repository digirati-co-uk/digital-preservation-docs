import 'dotenv/config'

// Presentation API base URL
export const iiifPresentationBaseURL: string = process.env.DLCS_PRESENTATION_BASEURL;
export const iiifOrchestratorBaseURL: string = process.env.DLCS_ORCHESTRATOR_BASEURL ?? iiifPresentationBaseURL?.replace("//presentation-api.", "//api.");

// Test customer credentials
export const iiifCustomerId: string = process.env.DLCS_CUSTOMER_ID;
export const iiifCredentials: string = generateCredentials(process.env.DLCS_USERNAME, process.env.DLCS_PASSWORD);

// Credentials for another customer - used to tests ensuring that customer A can't access resources owned by customer B
export const iiifOtherCustomerCredentials: string = generateCredentials(
    process.env.DLCS_OTHERCUSTOMER_USERNAME, process.env.DLCS_OTHERCUSTOMER_PASSWORD);

export function generateCredentials(username: string, password: string): string {
    const btoa = (str: string) => Buffer.from(str).toString('base64');
    return btoa(`${username}:${password}`);
}