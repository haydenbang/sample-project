import { describe, it, expect, expectTypeOf } from "vitest";
import type { ProductStatus, Product, ProductListResponse } from "./product";

// Helper to assert exhaustive checks at compile time
function assertNever(value: never): never {
  throw new Error(`Unexpected value: ${value}`);
}

function getStatusLabel(status: ProductStatus): string {
  switch (status) {
    case "ACTIVE":
      return "Active";
    case "ARCHIVED":
      return "Archived";
    case "DRAFT":
      return "Draft";
    case "LOW_STOCK":
      return "Low Stock";
    case "SOLD_OUT":
      return "Sold Out";
    default:
      return assertNever(status);
  }
}

describe("ProductStatus enum", () => {
  it("should include all expected status values", () => {
    const validStatuses: ProductStatus[] = [
      "ACTIVE",
      "ARCHIVED",
      "DRAFT",
      "LOW_STOCK",
      "SOLD_OUT",
    ];

    expect(validStatuses).toHaveLength(5);
    expect(validStatuses).toContain("ACTIVE");
    expect(validStatuses).toContain("ARCHIVED");
    expect(validStatuses).toContain("DRAFT");
    expect(validStatuses).toContain("LOW_STOCK");
    expect(validStatuses).toContain("SOLD_OUT");
  });

  it("should include the new LOW_STOCK status", () => {
    const status: ProductStatus = "LOW_STOCK";
    expect(status).toBe("LOW_STOCK");
  });

  it("should handle all statuses in exhaustive switch", () => {
    expect(getStatusLabel("ACTIVE")).toBe("Active");
    expect(getStatusLabel("ARCHIVED")).toBe("Archived");
    expect(getStatusLabel("DRAFT")).toBe("Draft");
    expect(getStatusLabel("LOW_STOCK")).toBe("Low Stock");
    expect(getStatusLabel("SOLD_OUT")).toBe("Sold Out");
  });

  it("should correctly identify LOW_STOCK as a valid ProductStatus type", () => {
    const status: ProductStatus = "LOW_STOCK";
    expectTypeOf(status).toEqualTypeOf<ProductStatus>();
  });
});

describe("Product interface", () => {
  it("should accept a product with LOW_STOCK status", () => {
    const product: Product = {
      id: 1,
      name: "Test Product",
      category: "Electronics",
      price: 99.99,
      stock: 3,
      status: "LOW_STOCK",
    };

    expect(product.status).toBe("LOW_STOCK");
    expect(product.id).toBe(1);
    expect(product.name).toBe("Test Product");
    expect(product.category).toBe("Electronics");
    expect(product.price).toBe(99.99);
    expect(product.stock).toBe(3);
  });

  it("should accept a product with ACTIVE status", () => {
    const product: Product = {
      id: 2,
      name: "Active Product",
      category: "Books",
      price: 19.99,
      stock: 100,
      status: "ACTIVE",
    };

    expect(product.status).toBe("ACTIVE");
  });

  it("should accept a product with ARCHIVED status", () => {
    const product: Product = {
      id: 3,
      name: "Archived Product",
      category: "Clothing",
      price: 49.99,
      stock: 0,
      status: "ARCHIVED",
    };

    expect(product.status).toBe("ARCHIVED");
  });

  it("should accept a product with DRAFT status", () => {
    const product: Product = {
      id: 4,
      name: "Draft Product",
      category: "Toys",
      price: 29.99,
      stock: 50,
      status: "DRAFT",
    };

    expect(product.status).toBe("DRAFT");
  });

  it("should accept a product with SOLD_OUT status", () => {
    const product: Product = {
      id: 5,
      name: "Sold Out Product",
      category: "Games",
      price: 59.99,
      stock: 0,
      status: "SOLD_OUT",
    };

    expect(product.status).toBe("SOLD_OUT");
  });

  it("should have the correct shape for a Product", () => {
    const product: Product = {
      id: 10,
      name: "Shape Test",
      category: "Test",
      price: 0,
      stock: 0,
      status: "DRAFT",
    };

    expect(product).toHaveProperty("id");
    expect(product).toHaveProperty("name");
    expect(product).toHaveProperty("category");
    expect(product).toHaveProperty("price");
    expect(product).toHaveProperty("stock");
    expect(product).toHaveProperty("status");
  });

  it("should type-check status field correctly", () => {
    const product: Product = {
      id: 1,
      name: "Type Check",
      category: "Test",
      price: 10,
      stock: 5,
      status: "LOW_STOCK",
    };

    expectTypeOf(product.status).toEqualTypeOf<ProductStatus>();
  });
});

describe("ProductListResponse interface", () => {
  it("should accept a list response with LOW_STOCK products", () => {
    const response: ProductListResponse = {
      items: [
        {
          id: 1,
          name: "Low Stock Item",
          category: "Electronics",
          price: 199.99,
          stock: 2,
          status: "LOW_STOCK",
        },
        {
          id: 2,
          name: "Active Item",
          category: "Electronics",
          price: 299.99,
          stock: 50,
          status: "ACTIVE",
        },
      ],
      total: 2,
      page: 1,
      size: 10,
    };

    expect(response.items).toHaveLength(2);
    expect(response.items[0].status).toBe("LOW_STOCK");
    expect(response.items[1].status).toBe("ACTIVE");
    expect(response.total).toBe(2);
    expect(response.page).toBe(1);
    expect(response.size).toBe(10);
  });

  it("should accept an empty items list", () => {
    const response: ProductListResponse = {
      items: [],
      total: 0,
      page: 1,
      size: 10,
    };

    expect(response.items).toHaveLength(0);
    expect(response.total).toBe(0);
  });

  it("should accept a list with all possible statuses", () => {
    const statuses: ProductStatus[] = [
      "ACTIVE",
      "ARCHIVED",
      "DRAFT",
      "LOW_STOCK",
      "SOLD_OUT",
    ];

    const response: ProductListResponse = {
      items: statuses.map((status, index) => ({
        id: index + 1,
        name: `Product ${index + 1}`,
        category: "Test",
        price: 10.0,
        stock: index * 5,
        status,
      })),
      total: statuses.length,
      page: 1,
      size: 20,
    };

    expect(response.items).toHaveLength(5);
    expect(response.items.map((item) => item.status)).toEqual([
      "ACTIVE",
      "ARCHIVED",
      "DRAFT",
      "LOW_STOCK",
      "SOLD_OUT",
    ]);
  });

  it("should have the correct shape for ProductListResponse", () => {
    const response: ProductListResponse = {
      items: [],
      total: 0,
      page: 1,
      size: 10,
    };

    expect(response).toHaveProperty("items");
    expect(response).toHaveProperty("total");
    expect(response).toHaveProperty("page");
    expect(response).toHaveProperty("size");
  });
});

describe("ProductStatus edge cases", () => {
  it("should not treat undefined as a valid ProductStatus at runtime", () => {
    const maybeStatus: ProductStatus | undefined = undefined;
    expect(maybeStatus).toBeUndefined();
  });

  it("should not treat null as a valid ProductStatus at runtime", () => {
    const maybeStatus: ProductStatus | null = null;
    expect(maybeStatus).toBeNull();
  });

  it("should correctly distinguish LOW_STOCK from SOLD_OUT", () => {
    const lowStock: ProductStatus = "LOW_STOCK";
    const soldOut: ProductStatus = "SOLD_OUT";

    expect(lowStock).not.toBe(soldOut);
    expect(lowStock).toBe("LOW_STOCK");
    expect(soldOut).toBe("SOLD_OUT");
  });

  it("should correctly distinguish LOW_STOCK from ACTIVE", () => {
    const lowStock: ProductStatus = "LOW_STOCK";
    const active: ProductStatus = "ACTIVE";

    expect(lowStock).not.toBe(active);
  });

  it("should handle status comparison correctly", () => {
    const product: Product = {
      id: 1,
      name: "Low Stock Product",
      category: "Test",
      price: 10,
      stock: 2,
      status: "LOW_STOCK",
    };

    expect(product.status === "LOW_STOCK").toBe(true);
    expect(product.status === "SOLD_OUT").toBe(false);
    expect(product.status === "ACTIVE").toBe(false);
  });

  it("should correctly filter products by LOW_STOCK status", () => {
    const products: Product[] = [
      {
        id: 1,
        name: "P1",
        category: "C",
        price: 10,
        stock: 100,
        status: "ACTIVE",
      },
      {
        id: 2,
        name: "P2",
        category: "C",
        price: 10,
        stock: 3,
        status: "LOW_STOCK",
      },
      {
        id: 3,
        name: "P3",
        category: "C",
        price: 10,
        stock: 0,
        status: "SOLD_OUT",
      },
      {
        id: 4,
        name: "P4",
        category: "C",
        price: 10,
        stock: 1,
        status: "LOW_STOCK",
      },
    ];

    const lowStockProducts = products.filter((p) => p.status === "LOW_STOCK");

    expect(lowStockProducts).toHaveLength(2);
    expect(lowStockProducts.map((p) => p.id)).toEqual([2, 4]);
  });

  it("should parse an API response string to ProductStatus correctly", () => {
    const apiResponseValue = "LOW_STOCK";
    const status = apiResponseValue as ProductStatus;
    expect(status).toBe("LOW_STOCK");
  });
});