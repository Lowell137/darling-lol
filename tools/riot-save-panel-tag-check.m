#import <AppKit/NSApplication.h>
#import <AppKit/NSSavePanel.h>
#import <AppKit/NSOpenPanel.h>
#import <Foundation/Foundation.h>
#import <objc/runtime.h>
#include <stdio.h>

/* Declarations only: implementations must come from the loaded AppKit, not
 * from linking a compatibility category directly into this probe. */
@interface NSSavePanel (RiotTagProbeDeclarations)
- (void)setShowsTagField:(BOOL)value;
- (BOOL)showsTagField;
- (void)setTagNames:(NSArray *)names;
- (NSArray *)tagNames;
@end

static BOOL emptyTags(NSSavePanel *panel) {
    NSArray *tags = [panel tagNames];
    return tags != nil && [tags isKindOfClass:[NSArray class]] && [tags count] == 0;
}

static BOOL checkPanel(Class panelClass) {
    SEL selectors[] = {@selector(setShowsTagField:), @selector(showsTagField),
                       @selector(setTagNames:), @selector(tagNames)};
    BOOL available = YES, inherited = YES, values = NO;
    /* This stateless probe must work without panel initialization. Bare runtime
     * allocation avoids NSWindow/nib/display setup; it does NOT test the chooser.
     * Dispose without running NSWindow's deallocator on an uninitialized panel. */
    NSSavePanel *panel = (NSSavePanel *)class_createInstance(panelClass, 0);
    for (unsigned i = 0; i < sizeof(selectors) / sizeof(selectors[0]); ++i) {
        Method base = class_getInstanceMethod([NSSavePanel class], selectors[i]);
        Method method = class_getInstanceMethod(panelClass, selectors[i]);
        available &= panel != nil && method != NULL && [panel respondsToSelector:selectors[i]];
        inherited &= base != NULL && method != NULL &&
            method_getImplementation(base) == method_getImplementation(method);
    }
    if (panelClass == [NSOpenPanel class])
        inherited &= class_getSuperclass(panelClass) == [NSSavePanel class];
    if (available) {
        @try {
            values = ![panel showsTagField] && emptyTags(panel);
            [panel setShowsTagField:YES];
            values &= ![panel showsTagField];
            [panel setShowsTagField:NO];
            values &= ![panel showsTagField];
            NSMutableArray *names = [NSMutableArray arrayWithObject:@"probe-tag"];
            [panel setTagNames:names];
            [names addObject:@"second-tag"];
            values &= emptyTags(panel);
            [panel setTagNames:[NSArray array]];
            values &= emptyTags(panel);
            [panel setTagNames:nil];
            values &= emptyTags(panel);
        } @catch (NSException *exception) {
            fprintf(stderr, "SAVE_PANEL_TAG exception=%s\n", [[exception name] UTF8String]);
            values = NO;
        }
    }
    if (panel != nil)
        object_dispose(panel);
    BOOL pass = available && inherited && values;
    printf("SAVE_PANEL_TAG class=%s selectors=%d inherited=%d values=%d pass=%d\n",
           class_getName(panelClass), available, inherited, values, pass);
    return pass;
}

int main(void) {
    @autoreleasepool {
        BOOL save = checkPanel([NSSavePanel class]);
        BOOL open = checkPanel([NSOpenPanel class]);
        printf("SAVE_PANEL_TAG_CHECK pass=%d\n", save && open);
        return save && open ? 0 : 1;
    }
}
