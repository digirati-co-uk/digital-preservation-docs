# Polymorphic Serialisation / Deserialisation

The Architectural Decision is to write CUSTOM deserialisers.

## Background

I had hoped to avoid this, by using System.Text.Json polymorphic support:

https://learn.microsoft.com/en-us/dotnet/standard/serialization/system-text-json/polymorphism

You can use a [Type Discriminator](https://learn.microsoft.com/en-us/dotnet/standard/serialization/system-text-json/polymorphism?pivots=dotnet-8-0#polymorphic-type-discriminators) which out of the box inserts an extra field into your serialised object, by default `"$type"`.

But this is JSON-LD 1.1, we already have a type discriminator - the field `type`!

After some experiments I could successfully serialise the following:

```c#

public abstract class Resource
{
    [JsonPropertyOrder(1)]
    [JsonPropertyName("id")]
    public Uri? Id { get; set; }

    [JsonPropertyOrder(2)]
    [JsonPropertyName("type")]
    public abstract string Type { get; set; }

    // other fields omitted
}


[JsonPolymorphic(TypeDiscriminatorPropertyName = "type")]
[JsonDerivedType(typeof(Container), typeDiscriminator: nameof(Container))]
[JsonDerivedType(typeof(Binary), typeDiscriminator: nameof(Binary))]
public abstract class PreservedResource : Resource
{
    [JsonPropertyOrder(10)]
    [JsonPropertyName("name")]
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public string? Name { get; set; }

    // other fields omitted
}


public class Container : PreservedResource
{
    public override string Type { get; set; } = nameof(Container);

    [JsonPropertyName("containers")]
    [JsonPropertyOrder(300)]
    public Container[]? Containers { get; set; } = [];

    // other fields omitted
}


public class Binary : PreservedResource
{
    public override string Type { get; set; } = nameof(Binary); 
    
    [JsonPropertyName("contentType")]
    [JsonPropertyOrder(300)]
    public string? ContentType { get; set; }

    // other fields omitted
}
```

```c#
    Resource resource = new Container();
    var json = JsonSerializer.Serialize(resource, jOpts);
    Console.WriteLine(json);
```    

```
{
  "id": "https://example.com/test",
  "type": "Container",
  "created": null,
  "createdBy": null,
  "lastModified": null,
  "lastModifiedBy": null
}
```

So far so good. But 

```c#
 Resource? deSer = JsonSerializer.Deserialize<Resource>(json);
```

This does not work, because the type discriminator MUST BE THE FIRST FIELD in the JSON!

https://github.com/dotnet/runtime/issues/96088

And then from that, I see https://github.com/dotnet/runtime/issues/72604#issuecomment-1279805812

> Avoid a JsonPolymorphicAttribute.TypeDiscriminatorPropertyName if it conflicts with a property in your type hierarchy.

Which I hadn't spotted in the documentation.

The Microsoft employee's answer to this is:

> The value of a string property can be arbitrary and might not necessarily reflect the runtime type of the object you are trying to serialize. In your example I would simply annotate the Type property with JsonIgnoreAttribute.

I can see the argument-ish... but " might not necessarily reflect the runtime type of the object" - Although in our case above the type discriminator value DOES actually match the type name, this doesn't matter - the type discriminator is just an arbitrary string! So I don't buy that.

This would suit JSON-LD types perfectly were it not for these two issues.

1. I don't want to insist that `type` appears first in the JSON string. This would be a ridiculous requirement for callers of the API.
2. I suppose we shouldn't go against MS recommendations on using an existing field. It works, and we would always insist in our world on a particular serialisation (e.g., always `"type"` never `"Type"`), but...

So we will instead do the interrogation of the JSON ourselves, extract the type, then deserialise to that type.

