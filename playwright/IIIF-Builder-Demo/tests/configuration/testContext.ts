import {test as base} from '@playwright/test';

export type TestOptions = {
    iiifCustomerId: string;
    iiifOtherCustomerCredentials: string;
    presentationMaxPageSize: number;
    presentationDefaultPageSize: number;
    apiCommon: CommonApiValues;
};

export type CommonApiValues = {
    rootPresentationUrl: string;
    rootHierarchicalUrl: string;
}

export const test = base.extend<TestOptions>({
    iiifCustomerId: ['2', {option: true}],
    presentationMaxPageSize: [1000, {option: true}],
    presentationDefaultPageSize: [100, {option: true}],
    apiCommon: [null, {option: true}]
});